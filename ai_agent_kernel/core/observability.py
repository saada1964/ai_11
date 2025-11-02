import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager
import json
import uuid
from config.logger import logger


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class TraceLevel(Enum):
    """Trace levels for different operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Metric data structure"""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str]
    timestamp: str
    unit: str = ""
    description: str = ""


@dataclass
class Trace:
    """Trace data structure"""
    trace_id: str
    span_id: str
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    status: str  # "success", "error", "timeout"
    labels: Dict[str, str]
    meta_data: Dict[str, Any]
    level: TraceLevel


class MetricCollector:
    """Collects and stores metrics"""
    
    def __init__(self):
        self.metrics: List[Metric] = []
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}
        
    def record_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None, 
                      description: str = ""):
        """Record a counter metric"""
        labels = labels or {}
        key = self._make_key(name, labels)
        
        if key not in self.counters:
            self.counters[key] = 0
        self.counters[key] += value
        
        metric = Metric(
            name=name,
            value=self.counters[key],
            metric_type=MetricType.COUNTER,
            labels=labels,
            timestamp=datetime.now().isoformat(),
            description=description
        )
        self.metrics.append(metric)
        logger.debug(f"Recorded counter metric: {name} = {self.counters[key]}")
    
    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None,
                    description: str = ""):
        """Record a gauge metric"""
        labels = labels or {}
        key = self._make_key(name, labels)
        self.gauges[key] = value
        
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels,
            timestamp=datetime.now().isoformat(),
            description=description
        )
        self.metrics.append(metric)
        logger.debug(f"Recorded gauge metric: {name} = {value}")
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None,
                        description: str = ""):
        """Record a histogram metric"""
        labels = labels or {}
        key = self._make_key(name, labels)
        
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
        
        # Keep only last 1000 values to prevent memory issues
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]
        
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            labels=labels,
            timestamp=datetime.now().isoformat(),
            description=description
        )
        self.metrics.append(metric)
        logger.debug(f"Recorded histogram metric: {name} = {value}")
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create a unique key for metric with labels"""
        if not labels:
            return name
        labels_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{labels_str}}}"
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all collected metrics"""
        return {
            "total_metrics": len(self.metrics),
            "counters": len(self.counters),
            "gauges": len(self.gauges),
            "histograms": len(self.histograms),
            "latest_timestamp": self.metrics[-1].timestamp if self.metrics else None
        }


class DistributedTracer:
    """Manages distributed tracing"""
    
    def __init__(self):
        self.active_spans: Dict[str, Trace] = {}
        self.completed_traces: List[Trace] = []
        self.trace_hierarchy: Dict[str, List[str]] = {}  # parent_span_id -> [child_span_ids]
    
    def start_trace(self, operation_name: str, trace_id: str = None, span_id: str = None,
                   labels: Dict[str, str] = None, level: TraceLevel = TraceLevel.MEDIUM) -> str:
        """Start a new trace span"""
        trace_id = trace_id or str(uuid.uuid4())
        span_id = span_id or str(uuid.uuid4())
        labels = labels or {}
        
        start_time = time.time()
        
        trace = Trace(
            trace_id=trace_id,
            span_id=span_id,
            operation_name=operation_name,
            start_time=start_time,
            end_time=0,
            duration=0,
            status="in_progress",
            labels=labels,
            meta_data={},
            level=level
        )
        
        self.active_spans[span_id] = trace
        logger.debug(f"Started trace span: {operation_name} ({span_id})")
        
        return span_id
    
    def end_trace(self, span_id: str, status: str = "success", meta_data: Dict[str, Any] = None):
        """End a trace span"""
        if span_id not in self.active_spans:
            logger.warning(f"Attempted to end non-existent span: {span_id}")
            return
        
        trace = self.active_spans[span_id]
        trace.end_time = time.time()
        trace.duration = trace.end_time - trace.start_time
        trace.status = status
        if meta_data:
            trace.meta_data.update(meta_data)
        
        # Move to completed traces
        self.completed_traces.append(trace)
        del self.active_spans[span_id]
        
        # Keep only last 10000 completed traces
        if len(self.completed_traces) > 10000:
            self.completed_traces = self.completed_traces[-10000:]
        
        logger.debug(f"Ended trace span: {trace.operation_name} ({span_id}) - {trace.duration:.3f}s")
    
    def link_traces(self, parent_span_id: str, child_span_id: str):
        """Link parent and child spans"""
        if parent_span_id not in self.trace_hierarchy:
            self.trace_hierarchy[parent_span_id] = []
        self.trace_hierarchy[parent_span_id].append(child_span_id)
    
    def get_trace_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get summary of traces within time window"""
        cutoff_time = time.time() - (hours_back * 3600)
        
        recent_traces = [
            trace for trace in self.completed_traces 
            if trace.start_time >= cutoff_time
        ]
        
        total_traces = len(recent_traces)
        successful_traces = len([t for t in recent_traces if t.status == "success"])
        error_traces = len([t for t in recent_traces if t.status == "error"])
        
        if recent_traces:
            avg_duration = sum(t.duration for t in recent_traces) / len(recent_traces)
            p95_duration = sorted([t.duration for t in recent_traces])[int(len(recent_traces) * 0.95)]
        else:
            avg_duration = 0
            p95_duration = 0
        
        return {
            "time_window_hours": hours_back,
            "total_traces": total_traces,
            "successful_traces": successful_traces,
            "error_traces": error_traces,
            "success_rate": successful_traces / total_traces if total_traces > 0 else 0,
            "average_duration": avg_duration,
            "p95_duration": p95_duration,
            "active_spans": len(self.active_spans)
        }


class PerformanceMonitor:
    """Monitors system performance metrics"""
    
    def __init__(self):
        self.metric_collector = MetricCollector()
        self.process = psutil.Process()
        
    async def collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metric_collector.record_gauge("system.cpu.usage_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.metric_collector.record_gauge("system.memory.usage_percent", memory.percent)
            self.metric_collector.record_gauge("system.memory.available_bytes", memory.available)
            self.metric_collector.record_gauge("system.memory.total_bytes", memory.total)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self.metric_collector.record_gauge("system.disk.usage_percent", disk.percent)
            self.metric_collector.record_gauge("system.disk.free_bytes", disk.free)
            self.metric_collector.record_gauge("system.disk.total_bytes", disk.total)
            
            # Process metrics
            self.metric_collector.record_gauge("process.cpu.usage_percent", self.process.cpu_percent())
            self.metric_collector.record_gauge("process.memory.usage_bytes", self.process.memory_info().rss)
            self.metric_collector.record_gauge("process.thread_count", self.process.num_threads())
            
            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                if network:
                    self.metric_collector.record_counter("network.bytes_sent", network.bytes_sent)
                    self.metric_collector.record_counter("network.bytes_recv", network.bytes_recv)
            except Exception:
                pass  # Network metrics might not be available in all environments
            
        except Exception as e:
            logger.error(f"System metrics collection error: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "usage_percent": memory.percent,
                    "available_bytes": memory.available,
                    "total_bytes": memory.total
                },
                "disk": {
                    "usage_percent": disk.percent,
                    "free_bytes": disk.free,
                    "total_bytes": disk.total
                }
            }
        except Exception as e:
            logger.error(f"Performance summary error: {e}")
            return {"error": str(e)}


class ObservabilityDashboard:
    """Creates observability dashboard data"""
    
    def __init__(self, metric_collector: MetricCollector, tracer: DistributedTracer,
                 performance_monitor: PerformanceMonitor):
        self.metric_collector = metric_collector
        self.tracer = tracer
        self.performance_monitor = performance_monitor
    
    def get_dashboard_data(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get complete dashboard data"""
        try:
            # Get system performance
            performance = self.performance_monitor.get_performance_summary()
            
            # Get trace summary
            trace_summary = self.tracer.get_trace_summary(time_range_hours)
            
            # Get metrics summary
            metrics_summary = self.metric_collector.get_metrics_summary()
            
            # Get recent traces for detailed analysis
            cutoff_time = time.time() - (time_range_hours * 3600)
            recent_traces = [
                asdict(trace) for trace in self.tracer.completed_traces
                if trace.start_time >= cutoff_time
            ]
            
            # Get recent metrics for analysis
            recent_metrics = [
                asdict(metric) for metric in self.metric_collector.metrics[-100:]  # Last 100 metrics
            ]
            
            # Calculate trends
            trends = self._calculate_trends(recent_metrics, recent_traces)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "time_range_hours": time_range_hours,
                "performance": performance,
                "tracing": trace_summary,
                "metrics": metrics_summary,
                "recent_traces": recent_traces,
                "recent_metrics": recent_metrics,
                "trends": trends,
                "alerts": self._generate_alerts(performance, trace_summary)
            }
            
        except Exception as e:
            logger.error(f"Dashboard data generation error: {e}")
            return {"error": str(e)}
    
    def _calculate_trends(self, metrics: List[Dict], traces: List[Dict]) -> Dict[str, Any]:
        """Calculate trends from recent data"""
        try:
            if not metrics or not traces:
                return {"error": "Insufficient data for trend analysis"}
            
            # Simple trend analysis
            # Response time trend (if available in traces)
            durations = [trace.get("duration", 0) for trace in traces if trace.get("duration")]
            if durations:
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                min_duration = min(durations)
            else:
                avg_duration = max_duration = min_duration = 0
            
            # Error rate trend
            error_count = len([t for t in traces if t.get("status") == "error"])
            success_count = len([t for t in traces if t.get("status") == "success"])
            total_count = error_count + success_count
            error_rate = error_count / total_count if total_count > 0 else 0
            
            return {
                "response_time": {
                    "average": avg_duration,
                    "max": max_duration,
                    "min": min_duration
                },
                "error_rate": error_rate,
                "throughput": len(traces) / max(1, (traces[-1]["start_time"] - traces[0]["start_time"]) if len(traces) > 1 else 1)
            }
            
        except Exception as e:
            logger.error(f"Trend calculation error: {e}")
            return {"error": str(e)}
    
    def _generate_alerts(self, performance: Dict, trace_summary: Dict) -> List[Dict[str, Any]]:
        """Generate alerts based on thresholds"""
        alerts = []
        
        try:
            # CPU usage alert
            cpu_percent = performance.get("cpu", {}).get("usage_percent", 0)
            if cpu_percent > 80:
                alerts.append({
                    "level": "warning",
                    "message": f"High CPU usage: {cpu_percent:.1f}%",
                    "metric": "cpu.usage_percent",
                    "value": cpu_percent,
                    "threshold": 80
                })
            
            # Memory usage alert
            memory_percent = performance.get("memory", {}).get("usage_percent", 0)
            if memory_percent > 85:
                alerts.append({
                    "level": "warning",
                    "message": f"High memory usage: {memory_percent:.1f}%",
                    "metric": "memory.usage_percent",
                    "value": memory_percent,
                    "threshold": 85
                })
            
            # Error rate alert
            error_rate = 1 - trace_summary.get("success_rate", 1.0)
            if error_rate > 0.05:  # 5% error rate threshold
                alerts.append({
                    "level": "error",
                    "message": f"High error rate: {error_rate:.1%}",
                    "metric": "error_rate",
                    "value": error_rate,
                    "threshold": 0.05
                })
            
            # Response time alert
            avg_duration = trace_summary.get("average_duration", 0)
            if avg_duration > 5.0:  # 5 second threshold
                alerts.append({
                    "level": "warning",
                    "message": f"High response time: {avg_duration:.2f}s",
                    "metric": "response_time",
                    "value": avg_duration,
                    "threshold": 5.0
                })
            
        except Exception as e:
            logger.error(f"Alert generation error: {e}")
        
        return alerts


class ObservabilityManager:
    """Main observability manager"""
    
    def __init__(self):
        self.metric_collector = MetricCollector()
        self.tracer = DistributedTracer()
        self.performance_monitor = PerformanceMonitor()
        self.dashboard = ObservabilityDashboard(
            self.metric_collector, self.tracer, self.performance_monitor
        )
        
        # Background tasks
        self._background_tasks = []
        self._running = False
    
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        if self._running:
            return
        
        self._running = True
        
        # Start system metrics collection
        asyncio.create_task(self._collect_system_metrics_loop())
        
        logger.info("Observability monitoring started")
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks"""
        self._running = False
        logger.info("Observability monitoring stopped")
    
    async def _collect_system_metrics_loop(self):
        """Background loop to collect system metrics"""
        while self._running:
            try:
                await self.performance_monitor.collect_system_metrics()
                await asyncio.sleep(30)  # Collect every 30 seconds
            except Exception as e:
                logger.error(f"System metrics collection loop error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    @asynccontextmanager
    async def trace_operation(self, operation_name: str, labels: Dict[str, str] = None,
                            level: TraceLevel = TraceLevel.MEDIUM):
        """Context manager for tracing operations"""
        span_id = self.tracer.start_trace(operation_name, labels=labels, level=level)
        start_time = time.time()
        
        try:
            yield span_id
            self.tracer.end_trace(span_id, "success")
        except Exception as e:
            self.tracer.end_trace(span_id, "error", {"error": str(e)})
            raise
        finally:
            duration = time.time() - start_time
            self.metric_collector.record_histogram("operation.duration", duration, labels)
    
    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
                    labels: Dict[str, str] = None, description: str = ""):
        """Record a metric"""
        if metric_type == MetricType.COUNTER:
            self.metric_collector.record_counter(name, value, labels, description)
        elif metric_type == MetricType.GAUGE:
            self.metric_collector.record_gauge(name, value, labels, description)
        elif metric_type == MetricType.HISTOGRAM:
            self.metric_collector.record_histogram(name, value, labels, description)
    
    def get_dashboard_data(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get complete dashboard data"""
        return self.dashboard.get_dashboard_data(time_range_hours)
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            performance = self.performance_monitor.get_performance_summary()
            trace_summary = self.tracer.get_trace_summary(1)  # Last hour
            
            # Determine overall health
            issues = []
            
            cpu_percent = performance.get("cpu", {}).get("usage_percent", 0)
            if cpu_percent > 90:
                issues.append("critical_cpu")
            elif cpu_percent > 80:
                issues.append("high_cpu")
            
            memory_percent = performance.get("memory", {}).get("usage_percent", 0)
            if memory_percent > 95:
                issues.append("critical_memory")
            elif memory_percent > 85:
                issues.append("high_memory")
            
            error_rate = 1 - trace_summary.get("success_rate", 1.0)
            if error_rate > 0.1:
                issues.append("high_error_rate")
            elif error_rate > 0.05:
                issues.append("elevated_error_rate")
            
            if not issues:
                status = "healthy"
            elif any("critical" in issue for issue in issues):
                status = "critical"
            elif any("high" in issue for issue in issues):
                status = "degraded"
            else:
                status = "warning"
            
            return {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "issues": issues,
                "performance": performance,
                "tracing_summary": trace_summary
            }
            
        except Exception as e:
            logger.error(f"System health check error: {e}")
            return {
                "status": "unknown",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global observability manager
observability_manager = ObservabilityManager()


# Decorator for easy operation tracing
def observe_operation(operation_name: str, labels: Dict[str, str] = None,
                     level: TraceLevel = TraceLevel.MEDIUM):
    """Decorator to automatically trace function operations"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            async with observability_manager.trace_operation(operation_name, labels, level):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we'll need to handle differently
            # For now, just execute without tracing
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator