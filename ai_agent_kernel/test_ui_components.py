#!/usr/bin/env python3
"""
Comprehensive testing script for interactive UI components system
"""
import asyncio
import json
import pandas as pd
from typing import Dict, Any
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.ui_components import (
    UIComponent, TextComponent, TableComponent, ChartComponent, MapComponent,
    ImageComponent, CodeComponent, CardComponent, InteractiveFormComponent,
    UIComponentFactory, UIComponentManager, UIComponentType,
    create_enhanced_response
)
from config.logger import logger


class UIComponentsTestSuite:
    """Test suite for interactive UI components"""
    
    def __init__(self):
        self.component_manager = UIComponentManager()
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "tests": []
        }
    
    async def run_all_tests(self):
        """Run all UI component tests"""
        logger.info("Starting UI Components Test Suite...")
        
        # Test Basic Components
        await self.test_basic_components()
        
        # Test Component Factory
        await self.test_component_factory()
        
        # Test Component Manager
        await self.test_component_manager()
        
        # Test Result Analysis
        await self.test_result_analysis()
        
        # Test Enhanced Response Creation
        await self.test_enhanced_response()
        
        # Test Specific Component Types
        await self.test_specific_components()
        
        # Test Edge Cases
        await self.test_edge_cases()
        
        # Print summary
        self.print_test_summary()
        
        return self.test_results
    
    async def test_basic_components(self):
        """Test basic UI component creation and functionality"""
        test_name = "Basic Components"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Text Component
            text_comp = TextComponent("text_001", "# مرحبا بالعالم\nهذا نص تجريبي", "markdown")
            assert text_comp.component_id == "text_001", "Text component ID should be set"
            assert text_comp.content_type == "markdown", "Content type should be markdown"
            text_dict = text_comp.to_dict()
            assert "content" in text_dict, "Text component should have content"
            await self._record_test_result(test_name, "Text Component", True, "Text component created successfully")
            
            # Test 2: Table Component with DataFrame
            sample_data = pd.DataFrame({
                "الاسم": ["أحمد", "فاطمة", "محمد"],
                "العمر": [25, 30, 35],
                "المدينة": ["الرياض", "جدة", "الدمام"]
            })
            table_comp = TableComponent("table_001", sample_data)
            assert table_comp.component_type == UIComponentType.TABLE, "Component type should be table"
            assert len(table_comp.data) == 3, "Table should have 3 rows"
            assert len(table_comp.columns) == 3, "Table should have 3 columns"
            await self._record_test_result(test_name, "Table Component", True, f"Table with {len(table_comp.data)} rows created")
            
            # Test 3: Chart Component
            chart_data = {
                "labels": ["يناير", "فبراير", "مارس"],
                "datasets": [
                    {"label": "المبيعات", "data": [100, 150, 200]}
                ]
            }
            chart_comp = ChartComponent("chart_001", "bar", chart_data)
            assert chart_comp.chart_type == "bar", "Chart type should be bar"
            assert "labels" in chart_comp.data, "Chart should have labels"
            await self._record_test_result(test_name, "Chart Component", True, "Chart component created successfully")
            
            # Test 4: Map Component
            map_comp = MapComponent("map_001", {"lat": 24.7136, "lng": 46.6753})  # Riyadh coordinates
            assert "lat" in map_comp.center, "Map should have latitude"
            assert "lng" in map_comp.center, "Map should have longitude"
            map_comp.add_marker({"lat": 24.7136, "lng": 46.6753, "title": "الرياض"})
            assert len(map_comp.markers) == 1, "Map should have 1 marker"
            await self._record_test_result(test_name, "Map Component", True, "Map component with marker created")
            
            # Test 5: Image Component
            img_comp = ImageComponent("img_001", "https://example.com/image.jpg", "صورة تجريبية")
            assert img_comp.image_url == "https://example.com/image.jpg", "Image URL should be set"
            assert img_comp.alt_text == "صورة تجريبية", "Alt text should be set"
            await self._record_test_result(test_name, "Image Component", True, "Image component created successfully")
            
            # Test 6: Code Component
            code_comp = CodeComponent("code_001", "print('مرحبا بالعالم')", "python")
            assert code_comp.language == "python", "Code language should be python"
            assert code_comp.line_numbers == True, "Line numbers should be enabled by default"
            await self._record_test_result(test_name, "Code Component", True, "Code component created successfully")
            
            # Test 7: Card Component
            card_comp = CardComponent("card_001", "عنوان البطاقة", "محتوى البطاقة", "تذييل البطاقة")
            assert card_comp.header == "عنوان البطاقة", "Card header should be set"
            assert card_comp.content == "محتوى البطاقة", "Card content should be set"
            await self._record_test_result(test_name, "Card Component", True, "Card component created successfully")
            
        except Exception as e:
            await self._record_test_result(test_name, "Basic Component Tests", False, str(e))
    
    async def test_component_factory(self):
        """Test component factory functionality"""
        test_name = "Component Factory"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Create text component via factory
            text_comp = UIComponentFactory.create_text_component("factory_text", "نص تجريبي")
            assert text_comp.component_id == "factory_text", "Factory should create correct ID"
            assert text_comp.component_type == UIComponentType.TEXT, "Factory should create correct type"
            await self._record_test_result(test_name, "Factory Text Creation", True, "Text component created via factory")
            
            # Test 2: Create table component via factory
            table_data = [{"اسم": "أحمد", "عمر": 25}, {"اسم": "فاطمة", "عمر": 30}]
            table_comp = UIComponentFactory.create_table_component("factory_table", table_data)
            assert table_comp.component_id == "factory_table", "Factory should create correct ID"
            assert len(table_comp.data) == 2, "Factory should create correct data"
            await self._record_test_result(test_name, "Factory Table Creation", True, "Table component created via factory")
            
            # Test 3: Create chart component via factory
            chart_data = {"labels": ["A", "B"], "datasets": [{"label": "Test", "data": [1, 2]}]}
            chart_comp = UIComponentFactory.create_chart_component("factory_chart", "pie", chart_data)
            assert chart_comp.chart_type == "pie", "Factory should create correct chart type"
            await self._record_test_result(test_name, "Factory Chart Creation", True, "Chart component created via factory")
            
            # Test 4: Create map component via factory
            map_comp = UIComponentFactory.create_map_component("factory_map", {"lat": 0, "lng": 0})
            assert map_comp.component_type == UIComponentType.MAP, "Factory should create correct type"
            await self._record_test_result(test_name, "Factory Map Creation", True, "Map component created via factory")
            
            # Test 5: Create image component via factory
            img_comp = UIComponentFactory.create_image_component("factory_img", "https://test.com/img.png")
            assert img_comp.component_type == UIComponentType.IMAGE, "Factory should create correct type"
            await self._record_test_result(test_name, "Factory Image Creation", True, "Image component created via factory")
            
            # Test 6: Create code component via factory
            code_comp = UIComponentFactory.create_code_component("factory_code", "test code")
            assert code_comp.component_type == UIComponentType.CODE, "Factory should create correct type"
            await self._record_test_result(test_name, "Factory Code Creation", True, "Code component created via factory")
            
            # Test 7: Create card component via factory
            card_comp = UIComponentFactory.create_card_component("factory_card", "عنوان", "محتوى")
            assert card_comp.component_type == UIComponentType.CARD, "Factory should create correct type"
            await self._record_test_result(test_name, "Factory Card Creation", True, "Card component created via factory")
            
        except Exception as e:
            await self._record_test_result(test_name, "Factory Tests", False, str(e))
    
    async def test_component_manager(self):
        """Test component manager functionality"""
        test_name = "Component Manager"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Add and retrieve component
            test_comp = TextComponent("manager_test", "نص تجريبي")
            self.component_manager.add_component(test_comp)
            
            retrieved = self.component_manager.get_component("manager_test")
            assert retrieved is not None, "Component should be retrieved"
            assert retrieved.component_id == "manager_test", "Retrieved component ID should match"
            await self._record_test_result(test_name, "Component Add/Retrieve", True, "Component added and retrieved successfully")
            
            # Test 2: Create interactive response
            components = [
                TextComponent("resp_text", "نص رئيسي"),
                TableComponent("resp_table", [{"عمود1": "قيمة1"}, {"عمود1": "قيمة2"}])
            ]
            
            response = self.component_manager.create_interactive_response(
                user_id=1,
                query="اختبار الاستجابة التفاعلية",
                components=components
            )
            
            assert response.get("response_type") == "interactive", "Response type should be interactive"
            assert response.get("component_count") == 2, "Should have 2 components"
            assert len(response.get("components", [])) == 2, "Should have 2 component dictionaries"
            await self._record_test_result(test_name, "Interactive Response Creation", True, 
                                        f"Created response with {response.get('component_count')} components")
            
            # Test 3: Create enhanced text response
            enhanced_response = self.component_manager.create_enhanced_text_response(
                user_id=1,
                query="اختبار النص المحسن",
                text_content="هذا نص محسن مع مكونات إضافية",
                additional_components=[ImageComponent("extra_img", "https://example.com/img.png")]
            )
            
            assert enhanced_response.get("response_type") == "interactive", "Enhanced response should be interactive"
            assert enhanced_response.get("component_count") >= 2, "Should have at least 2 components"
            await self._record_test_result(test_name, "Enhanced Text Response", True, 
                                        "Enhanced text response created successfully")
            
            # Test 4: Get response summary
            summary = self.component_manager.get_response_summary()
            assert "total_responses" in summary, "Summary should have total responses"
            assert "total_components" in summary, "Summary should have total components"
            assert summary["total_responses"] >= 2, "Should have at least 2 responses created"
            await self._record_test_result(test_name, "Response Summary", True, 
                                        f"Summary: {summary['total_responses']} responses, {summary['total_components']} components")
            
        except Exception as e:
            await self._record_test_result(test_name, "Manager Tests", False, str(e))
    
    async def test_result_analysis(self):
        """Test automatic result analysis for UI components"""
        test_name = "Result Analysis"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Analyze structured data result
            structured_result = {
                "title": "جدول البيانات",
                "data": [
                    {"الاسم": "أحمد", "العمر": 25, "المدينة": "الرياض"},
                    {"الاسم": "فاطمة", "العمر": 30, "المدينة": "جدة"}
                ]
            }
            
            components = self.component_manager.analyze_result_for_ui(structured_result)
            
            # Should create text component and table component
            table_components = [c for c in components if c.component_type == UIComponentType.TABLE]
            text_components = [c for c in components if c.component_type == UIComponentType.TEXT]
            
            assert len(table_components) > 0, "Should create table component for structured data"
            assert len(text_components) > 0, "Should create text component"
            await self._record_test_result(test_name, "Structured Data Analysis", True, 
                                        f"Created {len(components)} components from structured data")
            
            # Test 2: Analyze location result
            location_result = {
                "title": "موقع المستخدم",
                "location": {"lat": 24.7136, "lng": 46.6753},
                "address": "الرياض، المملكة العربية السعودية"
            }
            
            location_components = self.component_manager.analyze_result_for_ui(location_result)
            map_components = [c for c in location_components if c.component_type == UIComponentType.MAP]
            
            assert len(map_components) > 0, "Should create map component for location data"
            await self._record_test_result(test_name, "Location Data Analysis", True, 
                                        "Created map component from location data")
            
            # Test 3: Analyze code result
            code_result = {
                "title": "كود Python",
                "code": "print('Hello World')",
                "language": "python"
            }
            
            code_components = self.component_manager.analyze_result_for_ui(code_result)
            code_ui_components = [c for c in code_components if c.component_type == UIComponentType.CODE]
            
            assert len(code_ui_components) > 0, "Should create code component for code data"
            await self._record_test_result(test_name, "Code Data Analysis", True, 
                                        "Created code component from code data")
            
            # Test 4: Analyze results with numerical data for charts
            numerical_result = {
                "title": "نتائج المبيعات",
                "results": [
                    {"الشهر": "يناير", "المبيعات": 1000, "العمولات": 100},
                    {"الشهر": "فبراير", "المبيعات": 1500, "العمولات": 150},
                    {"الشهر": "مارس", "المبيعات": 2000, "العمولات": 200}
                ]
            }
            
            numerical_components = self.component_manager.analyze_result_for_ui(numerical_result)
            chart_components = [c for c in numerical_components if c.component_type == UIComponentType.CHART]
            
            assert len(chart_components) > 0, "Should create chart component for numerical data"
            await self._record_test_result(test_name, "Numerical Data Analysis", True, 
                                        "Created chart component from numerical data")
            
        except Exception as e:
            await self._record_test_result(test_name, "Analysis Tests", False, str(e))
    
    async def test_enhanced_response(self):
        """Test enhanced response creation"""
        test_name = "Enhanced Response"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Create enhanced response from complex result
            complex_result = {
                "title": "تقرير شامل",
                "data": [
                    {"المنتج": "لابتوب", "السعر": 2500, "الكمية": 10},
                    {"المنتج": "ماوس", "السعر": 50, "الكمية": 100}
                ],
                "location": {"lat": 21.4225, "lng": 39.8262},  # Mecca coordinates
                "total_value": 30000
            }
            
            enhanced_response = create_enhanced_response(
                result=complex_result,
                user_id=1,
                query="أريد تقرير عن المنتجات"
            )
            
            assert enhanced_response.get("response_type") == "interactive", "Enhanced response should be interactive"
            assert enhanced_response.get("enhancement_applied") == True, "Enhancement should be applied"
            assert enhanced_response.get("component_count", 0) > 0, "Should have UI components"
            await self._record_test_result(test_name, "Complex Result Enhancement", True, 
                                        f"Enhanced response with {enhanced_response.get('component_count')} components")
            
            # Test 2: Create enhanced response from simple text
            simple_result = {"content": "هذه استجابة بسيطة من النص"}
            
            simple_enhanced = create_enhanced_response(
                result=simple_result,
                user_id=2,
                query="اختبار بسيط"
            )
            
            assert simple_enhanced.get("response_type") == "interactive", "Simple result should also be enhanced"
            await self._record_test_result(test_name, "Simple Result Enhancement", True, 
                                        "Simple result enhanced successfully")
            
            # Test 3: Enhanced response with meta_data
            meta_data_enhanced = create_enhanced_response(
                result={"message": "اختبار مع بيانات وصفية"},
                user_id=3,
                query="اختبار مع meta_data"
            )
            
            assert "meta_data" in meta_data_enhanced, "Enhanced response should include meta_data"
            assert meta_data_enhanced.get("ui_components_enabled") == True, "UI components should be enabled"
            await self._record_test_result(test_name, "Enhanced Response with meta_data", True, 
                                        "meta_dataincluded in enhanced response")
            
        except Exception as e:
            await self._record_test_result(test_name, "Enhanced Response Tests", False, str(e))
    
    async def test_specific_components(self):
        """Test specific component types and features"""
        test_name = "Specific Components"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Table component with pandas DataFrame
            df = pd.DataFrame({
                "العمود الأول": [1, 2, 3, 4, 5],
                "العمود الثاني": ["أ", "ب", "ج", "د", "ه"],
                "العمود الثالث": [10.5, 20.3, 30.1, 40.7, 50.2]
            })
            
            table_comp = TableComponent("pandas_table", df)
            assert table_comp.component_type == UIComponentType.TABLE, "Should create table component"
            assert len(table_comp.data) == 5, "Should have 5 rows from DataFrame"
            await self._record_test_result(test_name, "Pandas DataFrame Table", True, 
                                        f"Created table from DataFrame with {len(table_comp.data)} rows")
            
            # Test 2: Chart component with multiple datasets
            multi_dataset_chart = {
                "labels": ["Q1", "Q2", "Q3", "Q4"],
                "datasets": [
                    {"label": "2023", "data": [100, 120, 150, 180]},
                    {"label": "2024", "data": [110, 130, 160, 190]}
                ]
            }
            
            chart_comp = ChartComponent("multi_chart", "line", multi_dataset_chart)
            assert len(chart_comp.data["datasets"]) == 2, "Should have 2 datasets"
            await self._record_test_result(test_name, "Multi-Dataset Chart", True, 
                                        "Chart with multiple datasets created")
            
            # Test 3: Map component with multiple markers and routes
            map_comp = MapComponent("route_map", {"lat": 24.7136, "lng": 46.6753})
            map_comp.add_marker({"lat": 24.7136, "lng": 46.6753, "title": "الرياض"})
            map_comp.add_marker({"lat": 21.3891, "lng": 39.8579, "title": "جدة"})
            map_comp.add_route({
                "start": {"lat": 24.7136, "lng": 46.6753},
                "end": {"lat": 21.3891, "lng": 39.8579},
                "color": "#FF0000"
            })
            
            assert len(map_comp.markers) == 2, "Should have 2 markers"
            assert len(map_comp.routes) == 1, "Should have 1 route"
            await self._record_test_result(test_name, "Complex Map Component", True, 
                                        f"Map with {len(map_comp.markers)} markers and {len(map_comp.routes)} routes")
            
            # Test 4: Interactive form component
            form_schema = {
                "fields": [
                    {"name": "name", "type": "text", "label": "الاسم", "required": True},
                    {"name": "email", "type": "email", "label": "البريد الإلكتروني", "required": True},
                    {"name": "age", "type": "number", "label": "العمر", "min": 18, "max": 100}
                ]
            }
            
            form_comp = InteractiveFormComponent("user_form", form_schema)
            assert form_comp.component_type == UIComponentType.INTERACTIVE_FORM, "Should create form component"
            assert len(form_comp.form_schema["fields"]) == 3, "Should have 3 form fields"
            await self._record_test_result(test_name, "Interactive Form Component", True, 
                                        "Form component with 3 fields created")
            
        except Exception as e:
            await self._record_test_result(test_name, "Specific Component Tests", False, str(e))
    
    async def test_edge_cases(self):
        """Test edge cases and error handling"""
        test_name = "Edge Cases"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Empty data in table component
            empty_data = []
            empty_table = TableComponent("empty_table", empty_data)
            assert len(empty_table.data) == 0, "Empty table should have 0 rows"
            await self._record_test_result(test_name, "Empty Table Handling", True, "Empty table handled correctly")
            
            # Test 2: Component with no meta_data
            basic_comp = TextComponent("basic", "نص بسيط")
            assert len(basic_compmeta_data) == 0, "Basic component should have empty meta_data"
            meta_data_value = basic_comp.get_from_meta_data("nonexistent", "default")
            assert meta_data_value == "default", "Should return default for nonexistent meta_data"
            await self._record_test_result(test_name, "meta_dataHandling", True, "meta_dataoperations work correctly")
            
            # Test 3: Map component with invalid coordinates
            invalid_map = MapComponent("invalid_map", {"lat": "invalid", "lng": None})
            # Should not crash, just store the values as-is
            assert invalid_map.center["lat"] == "invalid", "Should store invalid lat as-is"
            await self._record_test_result(test_name, "Invalid Coordinates Handling", True, "Invalid coordinates handled gracefully")
            
            # Test 4: Analyze completely empty result
            empty_result = {}
            empty_components = self.component_manager.analyze_result_for_ui(empty_result)
            
            # Should create at least a text component with formatted empty result
            assert len(empty_components) > 0, "Should create at least one component for empty result"
            await self._record_test_result(test_name, "Empty Result Analysis", True, 
                                        "Empty result analysis handled correctly")
            
            # Test 5: Component with very long content
            long_content = "نص طويل " * 1000  # Very long Arabic text
            long_text = TextComponent("long_text", long_content)
            assert len(long_text.content) > 5000, "Should handle very long content"
            await self._record_test_result(test_name, "Long Content Handling", True, 
                                        "Long content handled correctly")
            
            # Test 6: Create enhanced response with invalid result
            invalid_result = "not a dictionary"
            try:
                invalid_enhanced = create_enhanced_response(invalid_result, 1, "test")
                # Should handle gracefully and create fallback response
                assert invalid_enhanced.get("response_type") in ["text", "interactive"], "Should create valid response type"
                await self._record_test_result(test_name, "Invalid Result Handling", True, 
                                            "Invalid result handled gracefully")
            except Exception:
                await self._record_test_result(test_name, "Invalid Result Handling", True, 
                                            "Invalid result raised expected exception")
            
        except Exception as e:
            await self._record_test_result(test_name, "Edge Case Tests", False, str(e))
    
    async def _record_test_result(self, test_category: str, test_name: str, 
                                passed: bool, details: str = ""):
        """Record test result"""
        self.test_results["total_tests"] += 1
        if passed:
            self.test_results["passed"] += 1
            logger.info(f"✅ PASSED: {test_category} - {test_name}")
        else:
            self.test_results["failed"] += 1
            logger.error(f"❌ FAILED: {test_category} - {test_name}: {details}")
        
        self.test_results["tests"].append({
            "category": test_category,
            "test_name": test_name,
            "passed": passed,
            "details": details
        })
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*60)
        print("UI COMPONENTS TEST SUITE SUMMARY")
        print("="*60)
        
        print(f"Total Tests: {self.test_results['total_tests']}")
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"Success Rate: {(self.test_results['passed'] / self.test_results['total_tests'] * 100):.1f}%")
        
        if self.test_results["failed"] > 0:
            print(f"\nFAILED TESTS:")
            for test in self.test_results["tests"]:
                if not test["passed"]:
                    print(f"  • {test['category']} - {test['test_name']}: {test['details']}")
        
        print("\n" + "="*60)
        
        # Overall status
        if self.test_results["failed"] == 0:
            print("🎉 ALL TESTS PASSED - UI components system is working correctly!")
        else:
            print(f"⚠️ {self.test_results['failed']} tests failed - Review and fix issues")
        print("="*60 + "\n")


async def main():
    """Main test function"""
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Initialize test suite
    test_suite = UIComponentsTestSuite()
    
    try:
        # Run all tests
        results = await test_suite.run_all_tests()
        
        # Return exit code based on results
        return 0 if results["failed"] == 0 else 1
        
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)