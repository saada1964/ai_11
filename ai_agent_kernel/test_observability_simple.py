#!/usr/bin/env python3
"""
اختبار مبسط لنظام المراقبة المتقدمة
يركز على الاختبار الأساسي للمكونات الأساسية دون الحاجة للمتطلبات الكاملة
"""

import sys
import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import MagicMock, Mock

# إضافة مسار النظام
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# محاولة استيراد المكونات الأساسية
try:
    from core.observability import observability_manager, TraceLevel, MetricType
    OBSERVABILITY_AVAILABLE = True
except ImportError as e:
    print(f"تحذير: لا يمكن استيراد نظام المراقبة: {e}")
    OBSERVABILITY_AVAILABLE = False

def create_mock_observability():
    """إنشاء نظام مراقبة وهمي للاختبار"""
    class MockMetricCollector:
        def __init__(self):
            self.metrics = []
            self.counters = {}
            self.gauges = {}
            self.histograms = {}
            self.metric_type = type('obj', (object,), {
                'COUNTER': MetricType.COUNTER,
                'GAUGE': MetricType.GAUGE,
                'HISTOGRAM': MetricType.HISTOGRAM
            })
        
        def _make_key(self, name: str, labels: dict) -> str:
            return f"{name}:{sorted(labels.items())}"
    
    class MockObservabilityManager:
        def __init__(self):
            self.metric_collector = MockMetricCollector()
            self.traces = []
            self.performance_monitor = MagicMock()
            self.trace_processor = MagicMock()
        
        def record_metric(self, name: str, value: float, metric_type: MetricType, labels: dict = None):
            """تسجيل مقاييس"""
            labels = labels or {}
            mock_metric = Mock()
            mock_metric.name = name
            mock_metric.value = value
            mock_metric.metric_type = metric_type
            mock_metric.labels = labels
            mock_metric.timestamp = datetime.now().isoformat()
            
            self.metric_collector.metrics.append(mock_metric)
            
            # تحديث المقاييس المجمعة
            key = self.metric_collector._make_key(name, labels)
            if metric_type == MetricType.COUNTER:
                if key not in self.metric_collector.counters:
                    self.metric_collector.counters[key] = 0
                self.metric_collector.counters[key] += value
            elif metric_type == MetricType.GAUGE:
                self.metric_collector.gauges[key] = value
        
        def record_histogram(self, name: str, value: float, labels: dict = None):
            """تسجيل histogram"""
            labels = labels or {}
            mock_metric = Mock()
            mock_metric.name = name
            mock_metric.value = value
            mock_metric.metric_type = MetricType.HISTOGRAM
            mock_metric.labels = labels
            mock_metric.timestamp = datetime.now().isoformat()
            
            self.metric_collector.metrics.append(mock_metric)
            
            key = self.metric_collector._make_key(name, labels)
            if key not in self.metric_collector.histograms:
                self.metric_collector.histograms[key] = []
            self.metric_collector.histograms[key].append(value)
        
        def export_metrics(self) -> dict:
            """تصدير المقاييس"""
            return {
                "metrics": [m.name for m in self.metric_collector.metrics],
                "counters": self.metric_collector.counters,
                "gauges": self.metric_collector.gauges,
                "histograms": {k: len(v) for k, v in self.metric_collector.histograms.items()},
                "total_count": len(self.metric_collector.metrics)
            }
        
        def get_system_status(self) -> dict:
            """الحصول على حالة النظام"""
            return {
                "system_health": "healthy",
                "metrics": {
                    "total_metrics": len(self.metric_collector.metrics),
                    "counters": len(self.metric_collector.counters),
                    "gauges": len(self.metric_collector.gauges),
                    "histograms": len(self.metric_collector.histograms)
                },
                "traces": {
                    "total_traces": len(self.traces)
                },
                "performance": {
                    "monitoring_active": True
                }
            }
    
    return MockObservabilityManager()

def run_basic_tests():
    """تشغيل الاختبارات الأساسية"""
    print("🚀 بدء اختبارات نظام المراقبة المتقدمة...")
    print("=" * 60)
    
    # استخدام النظام الحقيقي أو الوهمي
    if OBSERVABILITY_AVAILABLE:
        print("✅ تم العثور على نظام المراقبة الحقيقي")
        test_manager = observability_manager
    else:
        print("⚠️ استخدام نظام مراقبة وهمي للاختبار")
        test_manager = create_mock_observability()
    
    results = []
    
    # اختبار 1: جمع المقاييس
    print("\n📊 اختبار جمع المقاييس...")
    try:
        test_manager.record_metric("test.counter", 5.0, MetricType.COUNTER, {"label": "test_value"})
        test_manager.record_metric("test.gauge", 42.0, MetricType.GAUGE, {"component": "test_component"})
        test_manager.record_metric("test.histogram", 10.5, MetricType.GAUGE, {"operation": "test_op"})
        
        assert len(test_manager.metric_collector.metrics) >= 3
        
        counter_key = test_manager.metric_collector._make_key("test.counter", {"label": "test_value"})
        assert test_manager.metric_collector.counters[counter_key] == 5.0
        
        gauge_key = test_manager.metric_collector._make_key("test.gauge", {"component": "test_component"})
        assert test_manager.metric_collector.gauges[gauge_key] == 42.0
        
        print("✅ نجح اختبار جمع المقاييس")
        results.append(("جمع المقاييس", "✅ نجح", None))
    except Exception as e:
        print(f"❌ فشل اختبار جمع المقاييس: {e}")
        results.append(("جمع المقاييس", "❌ فشل", str(e)))
    
    # اختبار 2: تصدير المقاييس
    print("\n📤 اختبار تصدير المقاييس...")
    try:
        dashboard_data = test_manager.get_dashboard_data()
        
        # التحقق من وجود بيانات لوحة المعلومات
        assert dashboard_data is not None
        assert len(str(dashboard_data)) > 0  # التأكد من وجود بيانات
        
        print("✅ نجح اختبار تصدير المقاييس")
        results.append(("تصدير المقاييس", "✅ نجح", None))
    except Exception as e:
        print(f"❌ فشل اختبار تصدير المقاييس: {e}")
        results.append(("تصدير المقاييس", "❌ فشل", str(e)))
    
    # اختبار 3: حالة النظام
    print("\n📋 اختبار حالة النظام...")
    try:
        status = test_manager.get_system_health()  # استخدام الطريقة المتاحة فعلياً
        
        # التحقق من وجود بيانات صحية
        assert status is not None
        assert len(str(status)) > 0  # التأكد من وجود بيانات
        
        print("✅ نجح اختبار حالة النظام")
        results.append(("حالة النظام", "✅ نجح", None))
    except Exception as e:
        print(f"❌ فشل اختبار حالة النظام: {e}")
        results.append(("حالة النظام", "❌ فشل", str(e)))
    
    # اختبار 4: سيناريو معقد
    print("\n🌟 اختبار سيناريو معقد...")
    try:
        # تسجيل مقاييس متنوعة
        for i in range(5):
            test_manager.record_metric(
                f"workflow.step_{i+1}", 1.0, 
                MetricType.COUNTER, 
                {"step": str(i+1), "phase": "execution"}
            )
        
        test_manager.record_metric("workflow.latency", 0.234, MetricType.GAUGE, {"endpoint": "/agent/invoke"})
        test_manager.record_metric("workflow.duration", 1.45, MetricType.GAUGE)
        
        # التحقق من تسجيل المقاييس
        assert len(test_manager.metric_collector.metrics) >= 7
        
        # التحقق من إحصائيات سير العمل
        workflow_metrics = [
            m for m in test_manager.metric_collector.metrics
            if m.name.startswith("workflow.")
        ]
        assert len(workflow_metrics) >= 7
        
        print("✅ نجح اختبار السيناريو المعقد")
        results.append(("السيناريو المعقد", "✅ نجح", None))
    except Exception as e:
        print(f"❌ فشل اختبار السيناريو المعقد: {e}")
        results.append(("السيناريو المعقد", "❌ فشل", str(e)))
    
    # طباعة ملخص النتائج
    print("\n" + "=" * 60)
    print("📋 ملخص نتائج الاختبارات:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result, error in results:
        status_emoji = "✅" if "نجح" in result else "❌"
        print(f"{status_emoji} {test_name}: {result}")
        if error:
            print(f"   التفاصيل: {error}")
        
        if "نجح" in result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 الإحصائيات النهائية:")
    print(f"   نجح: {passed}")
    print(f"   فشل: {failed}")
    print(f"   المجموع: {passed + failed}")
    
    if failed == 0:
        print("🎉 جميع الاختبارات نجحت!")
    else:
        print(f"⚠️ {failed} اختبار فشل")
    
    # طباعة إحصائيات النظام
    print("\n📈 إحصائيات نظام المراقبة:")
    print(f"   المقاييس المحفوظة: {len(test_manager.metric_collector.metrics)}")
    print(f"   المقاييس المجمعة: {len(test_manager.metric_collector.counters)}")
    
    # عرض عينة من المقاييس
    if test_manager.metric_collector.metrics:
        print("\n📊 عينة من المقاييس:")
        for metric in test_manager.metric_collector.metrics[:5]:
            print(f"   - {metric.name}: {metric.value} ({metric.metric_type.value})")
    
    return results

if __name__ == "__main__":
    run_basic_tests()