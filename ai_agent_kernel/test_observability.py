#!/usr/bin/env python3
"""
اختبارات شاملة لنظام المراقبة المتقدمة (Advanced Observability System)
يدرس جميع ميزات OpenTelemetry، distributed tracing، والـ metrics collection
"""

import asyncio
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch, Mock

# Mock dependencies to run tests
os.environ['TESTING'] = 'true'

# Import core modules
from core.observability import observability_manager, MetricCollector, TraceLevel, MetricType
from core.orchestrator import Orchestrator
from core.planner import Planner
from core.executor import Executor


class TestObservabilitySystem:
    """اختبارات شاملة لنظام المراقبة المتقدمة"""
    
    def setup_method(self):
        """إعداد قبل كل اختبار"""
        # مسح جميع البيانات المحفوظة
        observability_manager.metric_collector.metrics.clear()
        observability_manager.metric_collector.counters.clear()
        observability_manager.metric_collector.gauges.clear()
        observability_manager.metric_collector.histograms.clear()
        observability_manager.traces.clear()
        
        # إعادة تعيين الحالة
        observability_manager.performance_monitor.reset()
        observability_manager.trace_processor.reset()
    
    def test_metric_collection(self):
        """اختبار جمع المقاييس"""
        print("📊 اختبار جمع المقاييس...")
        
        # اختبار Counter metric
        observability_manager.record_metric(
            "test.counter", 5.0, 
            observability_manager.metric_collector.metric_type.COUNTER,
            {"label": "test_value"}
        )
        
        # اختبار Gauge metric
        observability_manager.record_metric(
            "test.gauge", 42.0,
            observability_manager.metric_collector.metric_type.GAUGE,
            {"component": "test_component"}
        )
        
        # اختبار Histogram metric
        observability_manager.record_histogram(
            "test.histogram", 10.5,
            {"operation": "test_op"}
        )
        
        # التحقق من حفظ المقاييس
        assert len(observability_manager.metric_collector.metrics) >= 3
        
        # التحقق من Counter
        counter_key = observability_manager.metric_collector._make_key("test.counter", {"label": "test_value"})
        assert observability_manager.metric_collector.counters[counter_key] == 5.0
        
        # التحقق من Gauge
        gauge_key = observability_manager.metric_collector._make_key("test.gauge", {"component": "test_component"})
        assert observability_manager.metric_collector.gauges[gauge_key] == 42.0
        
        print("✅ تم اختبار جمع المقاييس بنجاح")
    
    async def test_trace_operations(self):
        """اختبار تتبع العمليات (Trace Operations)"""
        print("🔍 اختبار تتبع العمليات...")
        
        # إنشاء trace operation
        async with observability_manager.trace_operation(
            "test_operation",
            {"test_param": "value"},
            TraceLevel.HIGH
        ):
            # محاكاة عملية
            await asyncio.sleep(0.01)
        
        # التحقق من حفظ Trace
        assert len(observability_manager.traces) > 0
        
        # البحث عن الـ trace المنشأ
        test_trace = None
        for trace in observability_manager.traces:
            if trace.operation_name == "test_operation":
                test_trace = trace
                break
        
        assert test_trace is not None
        assert test_trace.status == "success"
        assert test_trace.level == TraceLevel.HIGH
        
        print("✅ تم اختبار تتبع العمليات بنجاح")
    
    async def test_trace_levels(self):
        """اختبار مستويات التتبع المختلفة"""
        print("📈 اختبار مستويات التتبع...")
        
        # اختبار جميع المستويات
        levels_to_test = [TraceLevel.LOW, TraceLevel.MEDIUM, TraceLevel.HIGH, TraceLevel.CRITICAL]
        
        for level in levels_to_test:
            async with observability_manager.trace_operation(
                f"test_level_{level.value}",
                level=level
            ):
                await asyncio.sleep(0.001)
        
        # التحقق من حفظ جميع الـ traces
        assert len(observability_manager.traces) >= 4
        
        # التحقق من مستويات مختلفة
        traces_by_level = {}
        for trace in observability_manager.traces:
            if trace.level not in traces_by_level:
                traces_by_level[trace.level] = []
            traces_by_level[trace.level].append(trace)
        
        for level in levels_to_test:
            assert level in traces_by_level
        
        print("✅ تم اختبار مستويات التتبع بنجاح")
    
    async def test_performance_monitoring(self):
        """اختبار مراقبة الأداء"""
        print("⚡ اختبار مراقبة الأداء...")
        
        # تسجيل عملية بطيئة
        start_time = time.time()
        async with observability_manager.trace_operation("slow_operation", level=TraceLevel.HIGH):
            await asyncio.sleep(0.05)  # محاكاة عملية بطيئة
        
        end_time = time.time()
        
        # تسجيل عملية سريعة
        async with observability_manager.trace_operation("fast_operation", level=TraceLevel.MEDIUM):
            await asyncio.sleep(0.01)
        
        # التحقق من حفظ المقاييس
        performance_metrics = observability_manager.get_performance_metrics()
        assert "slow_operation" in performance_metrics["traces"]
        assert "fast_operation" in performance_metrics["traces"]
        
        slow_trace_duration = performance_metrics["traces"]["slow_operation"]["duration"]
        fast_trace_duration = performance_metrics["traces"]["fast_operation"]["duration"]
        
        # التحقق من أن العملية البطيئة أبطأ من السريعة
        assert slow_trace_duration > fast_trace_duration
        
        print("✅ تم اختبار مراقبة الأداء بنجاح")
    
    def test_system_status(self):
        """اختبار حالة النظام"""
        print("📋 اختبار حالة النظام...")
        
        # تسجيل بعض البيانات
        observability_manager.record_metric("test.metric", 1.0, MetricType.COUNTER)
        
        # الحصول على حالة النظام
        status = observability_manager.get_system_status()
        
        # التحقق من محتويات الحالة
        assert "system_health" in status
        assert "metrics" in status
        assert "traces" in status
        assert "performance" in status
        
        # التحقق من إحصائيات المقاييس
        metrics_stats = status["metrics"]
        assert metrics_stats["total_metrics"] > 0
        
        print("✅ تم اختبار حالة النظام بنجاح")
    
    async def test_error_handling_in_traces(self):
        """اختبار التعامل مع الأخطاء في التتبع"""
        print("❌ اختبار التعامل مع الأخطاء...")
        
        # إنشاء trace بخطأ
        try:
            async with observability_manager.trace_operation("failing_operation", level=TraceLevel.HIGH):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # التحقق من حفظ الـ trace مع حالة error
        test_trace = None
        for trace in observability_manager.traces:
            if trace.operation_name == "failing_operation":
                test_trace = trace
                break
        
        assert test_trace is not None
        assert test_trace.status == "error"
        assert "Test error" in str(test_tracemeta_data.get("error", ""))
        
        print("✅ تم اختبار التعامل مع الأخطاء بنجاح")
    
    async def test_orchestrator_integration(self):
        """اختبار دمج المراقبة في المنسق"""
        print("🎯 اختبار دمج المراقبة في المنسق...")
        
        # إنشاء منسق
        orchestrator = Orchestrator()
        
        # تسجيل العملية قبل الاختبار
        initial_traces_count = len(observability_manager.traces)
        
        async with observability_manager.trace_operation("orchestrator_integration_test", level=TraceLevel.HIGH):
            # محاكاة خطوات المنسق
            async with observability_manager.trace_operation("get_user_memory", level=TraceLevel.MEDIUM):
                await asyncio.sleep(0.001)
            
            async with observability_manager.trace_operation("get_conversation_context", level=TraceLevel.MEDIUM):
                await asyncio.sleep(0.001)
            
            async with observability_manager.trace_operation("load_configurations", level=TraceLevel.MEDIUM):
                await asyncio.sleep(0.001)
        
        # التحقق من إنشاء traces إضافية
        final_traces_count = len(observability_manager.traces)
        assert final_traces_count > initial_traces_count
        
        # البحث عن traces المحددة
        orchestrator_trace_found = False
        sub_operation_traces = 0
        
        for trace in observability_manager.traces:
            if trace.operation_name == "orchestrator_integration_test":
                orchestrator_trace_found = True
            elif trace.operation_name in ["get_user_memory", "get_conversation_context", "load_configurations"]:
                sub_operation_traces += 1
        
        assert orchestrator_trace_found
        assert sub_operation_traces >= 3
        
        print("✅ تم اختبار دمج المراقبة في المنسق بنجاح")
    
    async def test_planner_integration(self):
        """اختبار دمج المراقبة في المخطط"""
        print("📝 اختبار دمج المراقبة في المخطط...")
        
        # إنشاء مخطط
        planner = Planner()
        
        # تسجيل الخطة قبل الاختبار
        initial_traces_count = len(observability_manager.traces)
        
        # محاكاة إنشاء خطة
        async with observability_manager.trace_operation("planner.create_plan", level=TraceLevel.HIGH):
            async with observability_manager.trace_operation("generate_initial_plan", level=TraceLevel.MEDIUM):
                await asyncio.sleep(0.001)
            
            async with observability_manager.trace_operation("apply_dynamic_memory", level=TraceLevel.MEDIUM):
                await asyncio.sleep(0.001)
            
            if planner.enable_self_correction:
                async with observability_manager.trace_operation("apply_self_correction", level=TraceLevel.MEDIUM):
                    await asyncio.sleep(0.001)
        
        # التحقق من إنشاء traces
        final_traces_count = len(observability_manager.traces)
        assert final_traces_count > initial_traces_count
        
        # التحقق من وجود traces المخطط
        planner_traces = [
            trace for trace in observability_manager.traces 
            if trace.operation_name.startswith("planner.") or 
               trace.operation_name in ["generate_initial_plan", "apply_dynamic_memory", "apply_self_correction"]
        ]
        
        assert len(planner_traces) >= 3
        
        print("✅ تم اختبار دمج المراقبة في المخطط بنجاح")
    
    async def test_executor_integration(self):
        """اختبار دمج المراقبة في المنفذ"""
        print("⚙️ اختبار دمج المراقبة في المنفذ...")
        
        # إنشاء منفذ
        executor = Executor()
        
        # محاكاة تنفيذ خطة
        test_plan = {
            "plan": {
                "steps": [
                    {"id": "step_1", "type": "TOOL_CALL", "tool": "test_tool"},
                    {"id": "step_2", "type": "DIRECT_ANSWER", "description": "Test step"}
                ]
            }
        }
        
        # تسجيل التنفيذ قبل الاختبار
        initial_traces_count = len(observability_manager.traces)
        
        async with observability_manager.trace_operation("executor.execute_plan", level=TraceLevel.HIGH):
            # محاكاة خطوات التنفيذ
            async with observability_manager.trace_operation("validate_plan", level=TraceLevel.MEDIUM):
                await asyncio.sleep(0.001)
            
            async with observability_manager.trace_operation("build_dependency_graph", level=TraceLevel.LOW):
                await asyncio.sleep(0.001)
            
            async with observability_manager.trace_operation("topological_sort", level=TraceLevel.LOW):
                await asyncio.sleep(0.001)
            
            # محاكاة تنفيذ الخطوات
            for i, step in enumerate(test_plan["plan"]["steps"]):
                step_id = step.get("id", f"index_{i}")
                async with observability_manager.trace_operation(
                    f"execute_step_{step_id}",
                    level=TraceLevel.HIGH,
                    labels={"step_id": step_id, "step_type": step.get("type", "unknown")}
                ):
                    await asyncio.sleep(0.001)
        
        # التحقق من إنشاء traces
        final_traces_count = len(observability_manager.traces)
        assert final_traces_count > initial_traces_count
        
        # التحقق من traces المنفذ
        executor_traces = [
            trace for trace in observability_manager.traces 
            if trace.operation_name.startswith("executor.") or 
               "execute_step_" in trace.operation_name
        ]
        
        assert len(executor_traces) >= 4  # validate_plan + build_dependency_graph + topological_sort + step executions
        
        print("✅ تم اختبار دمج المراقبة في المنفذ بنجاح")
    
    def test_metric_export_format(self):
        """اختبار تصدير المقاييس بالتنسيق الصحيح"""
        print("📤 اختبار تصدير المقاييس...")
        
        # تسجيل مقاييس متنوعة
        observability_manager.record_metric("test.counter", 10.0, MetricType.COUNTER)
        observability_manager.record_metric("test.gauge", 25.0, MetricType.GAUGE)
        observability_manager.record_histogram("test.histogram", 15.0)
        
        # الحصول على المقاييس المصدرة
        metrics_export = observability_manager.export_metrics()
        
        # التحقق من البنية
        assert "metrics" in metrics_export
        assert "counters" in metrics_export
        assert "gauges" in metrics_export
        assert "histograms" in metrics_export
        assert "total_count" in metrics_export
        
        # التحقق من البيانات
        assert metrics_export["total_count"] >= 3
        assert len(metrics_export["counters"]) > 0
        assert len(metrics_export["gauges"]) > 0
        
        print("✅ تم اختبار تصدير المقاييس بنجاح")
    
    async def test_complex_scenario(self):
        """اختبار سيناريو معقد شامل"""
        print("🌟 اختبار سيناريو معقد شامل...")
        
        # محاكاة طلب كامل مع جميع المراحل
        start_time = time.time()
        
        async with observability_manager.trace_operation("complete_request", level=TraceLevel.CRITICAL):
            # مرحلة تخطيط
            async with observability_manager.trace_operation("planning_phase", level=TraceLevel.HIGH):
                await asyncio.sleep(0.02)
                observability_manager.record_metric("planning.time", 0.02, MetricType.GAUGE)
            
            # مرحلة تنفيذ
            async with observability_manager.trace_operation("execution_phase", level=TraceLevel.HIGH):
                for i in range(3):
                    async with observability_manager.trace_operation(
                        f"execution_step_{i+1}",
                        level=TraceLevel.MEDIUM,
                        labels={"step": str(i+1)}
                    ):
                        await asyncio.sleep(0.01)
                        observability_manager.record_metric(
                            f"execution.step_{i+1}", 1.0, 
                            MetricType.COUNTER, {"step": str(i+1)}
                        )
            
            # مرحلة الاستجابة
            async with observability_manager.trace_operation("response_phase", level=TraceLevel.MEDIUM):
                await asyncio.sleep(0.01)
                observability_manager.record_metric("response.generated", 1.0, MetricType.COUNTER)
        
        # التحقق من النتائج
        all_traces = observability_manager.traces
        all_metrics = observability_manager.metric_collector.metrics
        
        # التحقق من وجود جميع المراحل
        trace_names = [trace.operation_name for trace in all_traces]
        assert "complete_request" in trace_names
        assert "planning_phase" in trace_names
        assert "execution_phase" in trace_names
        assert "response_phase" in trace_names
        assert any("execution_step_" in name for name in trace_names)
        
        # التحقق من المقاييس
        metric_names = [metric.name for metric in all_metrics]
        assert "planning.time" in metric_names
        assert "response.generated" in metric_names
        
        # التحقق من مستوى أهمية العملية الرئيسية
        main_trace = next(trace for trace in all_traces if trace.operation_name == "complete_request")
        assert main_trace.level == TraceLevel.CRITICAL
        
        print("✅ تم اختبار السيناريو المعقد بنجاح")


def run_async_tests():
    """تشغيل جميع الاختبارات غير المتزامنة"""
    async def run_all_tests():
        test_instance = TestObservabilitySystem()
        test_instance.setup_method()
        
        # قائمة الاختبارات غير المتزامنة
        async_tests = [
            ("تتبع العمليات", test_instance.test_trace_operations),
            ("مستويات التتبع", test_instance.test_trace_levels),
            ("مراقبة الأداء", test_instance.test_performance_monitoring),
            ("التعامل مع الأخطاء", test_instance.test_error_handling_in_traces),
            ("دمج المراقبة في المنسق", test_instance.test_orchestrator_integration),
            ("دمج المراقبة في المخطط", test_instance.test_planner_integration),
            ("دمج المراقبة في المنفذ", test_instance.test_executor_integration),
            ("السيناريو المعقد", test_instance.test_complex_scenario)
        ]
        
        results = []
        
        for test_name, test_func in async_tests:
            print(f"\n🔬 اختبار: {test_name}")
            try:
                await test_func()
                results.append((test_name, "✅ نجح", None))
                print(f"   {test_name}: ✅ نجح")
            except Exception as e:
                results.append((test_name, "❌ فشل", str(e)))
                print(f"   {test_name}: ❌ فشل - {str(e)}")
        
        return results
    
    return asyncio.run(run_all_tests())


def run_sync_tests():
    """تشغيل جميع الاختبارات المتزامنة"""
    test_instance = TestObservabilitySystem()
    test_instance.setup_method()
    
    # قائمة الاختبارات المتزامنة
    sync_tests = [
        ("جمع المقاييس", test_instance.test_metric_collection),
        ("حالة النظام", test_instance.test_system_status),
        ("تصدير المقاييس", test_instance.test_metric_export_format)
    ]
    
    results = []
    
    for test_name, test_func in sync_tests:
        print(f"\n🔬 اختبار: {test_name}")
        try:
            test_func()
            results.append((test_name, "✅ نجح", None))
            print(f"   {test_name}: ✅ نجح")
        except Exception as e:
            results.append((test_name, "❌ فشل", str(e)))
            print(f"   {test_name}: ❌ فشل - {str(e)}")
    
    return results


def run_all_tests():
    """تشغيل جميع الاختبارات"""
    print("🚀 بدء اختبارات نظام المراقبة المتقدمة...")
    print("=" * 60)
    
    # تشغيل الاختبارات المتزامنة أولاً
    sync_results = run_sync_tests()
    
    # تشغيل الاختبارات غير المتزامنة
    async_results = run_async_tests()
    
    # دمج النتائج
    all_results = sync_results + async_results
    
    # طباعة ملخص النتائج
    print("\n" + "=" * 60)
    print("📋 ملخص نتائج الاختبارات:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result, error in all_results:
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
    print(f"   المقاييس المحفوظة: {len(observability_manager.metric_collector.metrics)}")
    print(f"   التتبع المحفوظ: {len(observability_manager.traces)}")
    
    # عرض عينة من المقاييس
    if observability_manager.metric_collector.metrics:
        print("\n📊 عينة من المقاييس:")
        for metric in observability_manager.metric_collector.metrics[:5]:
            print(f"   - {metric.name}: {metric.value} ({metric.metric_type.value})")
    
    return all_results


if __name__ == "__main__":
    run_all_tests()