import json
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from config.logger import logger


class UIComponentType(Enum):
    """Types of UI components that can be returned"""
    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    MAP = "map"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    FILE_DOWNLOAD = "file_download"
    INTERACTIVE_FORM = "interactive_form"
    PROGRESS_BAR = "progress_bar"
    ALERT = "alert"
    CARD = "card"
    LIST = "list"
    GRID = "grid"


class UIComponent(ABC):
    """Base class for UI components"""
    
    def __init__(self, component_id: str, component_type: UIComponentType, title: str = ""):
        self.component_id = component_id
        self.component_type = component_type
        self.title = title
        self.meta_data= {}
        self.timestamp = datetime.now().isoformat()
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert component to dictionary representation"""
        pass
    
    def add_meta_data(self, key: str, value: Any):
        """Add meta_datato component"""
        self.meta_data[key] = value
    
    def get_meta_data(self, key: str, default=None) -> Any:
        """Get meta_datavalue"""
        return self.meta_data.get(key, default)


class TextComponent(UIComponent):
    """Text-based UI component"""
    
    def __init__(self, component_id: str, content: str, content_type: str = "markdown"):
        super().__init__(component_id, UIComponentType.TEXT)
        self.content = content
        self.content_type = content_type  # markdown, plain_text, html
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type,
            "meta_data": self.meta_data,
            "timestamp": self.timestamp
        }


class TableComponent(UIComponent):
    """Table-based UI component"""
    
    def __init__(self, component_id: str, data: Union[List[Dict], pd.DataFrame], 
                 columns: Optional[List[str]] = None):
        super().__init__(component_id, UIComponentType.TABLE)
        
        if isinstance(data, pd.DataFrame):
            self.data = data.to_dict('records')
            self.columns = columns or list(data.columns)
        else:
            self.data = data
            self.columns = columns or (list(data[0].keys()) if data else [])
        
        self.sortable = True
        self.filterable = True
        self.pagination = {"enabled": True, "page_size": 10}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "title": self.title,
            "data": self.data,
            "columns": self.columns,
            "sortable": self.sortable,
            "filterable": self.filterable,
            "pagination": self.pagination,
            "meta_data": self.meta_data,
            "timestamp": self.timestamp
        }


class ChartComponent(UIComponent):
    """Chart/graph UI component"""
    
    def __init__(self, component_id: str, chart_type: str, data: Dict[str, Any]):
        super().__init__(component_id, UIComponentType.CHART)
        self.chart_type = chart_type  # line, bar, pie, scatter, histogram, etc.
        self.data = data
        
        # Common chart configurations
        self.config = {
            "width": 800,
            "height": 400,
            "responsive": True,
            "legend": True,
            "grid": True
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "title": self.title,
            "chart_type": self.chart_type,
            "data": self.data,
            "config": self.config,
            "meta_data": self.meta_data,
            "timestamp": self.timestamp
        }


class MapComponent(UIComponent):
    """Map/location-based UI component"""
    
    def __init__(self, component_id: str, center: Dict[str, float], zoom: int = 10):
        super().__init__(component_id, UIComponentType.MAP)
        self.center = center  # {"lat": 0.0, "lng": 0.0}
        self.zoom = zoom
        self.markers = []
        self.polygons = []
        self.routes = []
    
    def add_marker(self, marker: Dict[str, Any]):
        """Add marker to map"""
        self.markers.append(marker)
    
    def add_polygon(self, polygon: Dict[str, Any]):
        """Add polygon to map"""
        self.polygons.append(polygon)
    
    def add_route(self, route: Dict[str, Any]):
        """Add route to map"""
        self.routes.append(route)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "title": self.title,
            "center": self.center,
            "zoom": self.zoom,
            "markers": self.markers,
            "polygons": self.polygons,
            "routes": self.routes,
            "meta_data": self.meta_data,
            "timestamp": self.timestamp
        }


class ImageComponent(UIComponent):
    """Image UI component"""
    
    def __init__(self, component_id: str, image_url: str, alt_text: str = ""):
        super().__init__(component_id, UIComponentType.IMAGE)
        self.image_url = image_url
        self.alt_text = alt_text
        self.width = None
        self.height = None
        self.caption = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "title": self.title,
            "image_url": self.image_url,
            "alt_text": self.alt_text,
            "width": self.width,
            "height": self.height,
            "caption": self.caption,
            "meta_data": self.meta_data,
            "timestamp": self.timestamp
        }


class CodeComponent(UIComponent):
    """Code/highlighted text UI component"""
    
    def __init__(self, component_id: str, code: str, language: str = "text"):
        super().__init__(component_id, UIComponentType.CODE)
        self.code = code
        self.language = language
        self.line_numbers = True
        self.theme = "github"  # github, monokai, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "title": self.title,
            "code": self.code,
            "language": self.language,
            "line_numbers": self.line_numbers,
            "theme": self.theme,
            "meta_data": self.meta_data,
            "timestamp": self.timestamp
        }


class InteractiveFormComponent(UIComponent):
    """Interactive form UI component"""
    
    def __init__(self, component_id: str, form_schema: Dict[str, Any]):
        super().__init__(component_id, UIComponentType.INTERACTIVE_FORM)
        self.form_schema = form_schema
        self.submit_action = ""
        self.validation_rules = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "title": self.title,
            "form_schema": self.form_schema,
            "submit_action": self.submit_action,
            "validation_rules": self.validation_rules,
            "meta_data": self.meta_data,
            "timestamp": self.timestamp
        }


class CardComponent(UIComponent):
    """Card UI component for grouped content"""
    
    def __init__(self, component_id: str, header: str, content: str, footer: str = ""):
        super().__init__(component_id, UIComponentType.CARD)
        self.header = header
        self.content = content
        self.footer = footer
        self.style = "default"  # default, elevated, outlined
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "title": self.title,
            "header": self.header,
            "content": self.content,
            "footer": self.footer,
            "style": self.style,
            "meta_data": self.meta_data,
            "timestamp": self.timestamp
        }


class UIComponentFactory:
    """Factory for creating UI components"""
    
    @staticmethod
    def create_text_component(component_id: str, content: str, 
                            content_type: str = "markdown") -> TextComponent:
        """Create a text component"""
        return TextComponent(component_id, content, content_type)
    
    @staticmethod
    def create_table_component(component_id: str, data: Union[List[Dict], pd.DataFrame],
                             columns: Optional[List[str]] = None) -> TableComponent:
        """Create a table component"""
        return TableComponent(component_id, data, columns)
    
    @staticmethod
    def create_chart_component(component_id: str, chart_type: str, 
                             data: Dict[str, Any]) -> ChartComponent:
        """Create a chart component"""
        return ChartComponent(component_id, chart_type, data)
    
    @staticmethod
    def create_map_component(component_id: str, center: Dict[str, float],
                           zoom: int = 10) -> MapComponent:
        """Create a map component"""
        return MapComponent(component_id, center, zoom)
    
    @staticmethod
    def create_image_component(component_id: str, image_url: str,
                             alt_text: str = "") -> ImageComponent:
        """Create an image component"""
        return ImageComponent(component_id, image_url, alt_text)
    
    @staticmethod
    def create_code_component(component_id: str, code: str,
                            language: str = "text") -> CodeComponent:
        """Create a code component"""
        return CodeComponent(component_id, code, language)
    
    @staticmethod
    def create_card_component(component_id: str, header: str, content: str,
                            footer: str = "") -> CardComponent:
        """Create a card component"""
        return CardComponent(component_id, header, content, footer)


class UIComponentManager:
    """Manager for UI components and responses"""
    
    def __init__(self):
        self.components = {}
        self.response_queue = []
    
    def add_component(self, component: UIComponent):
        """Add a component to the manager"""
        self.components[component.component_id] = component
        logger.debug(f"Added UI component: {component.component_type.value}")
    
    def get_component(self, component_id: str) -> Optional[UIComponent]:
        """Get a component by ID"""
        return self.components.get(component_id)
    
    def create_interactive_response(self, user_id: int, query: str,
                                  components: List[UIComponent],
                                  meta_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a complete interactive response"""
        # Add all components
        for component in components:
            self.add_component(component)
        
        # Create response structure
        response = {
            "user_id": user_id,
            "query": query,
            "response_type": "interactive",
            "components": [comp.to_dict() for comp in components],
            "component_count": len(components),
            "timestamp": datetime.now().isoformat(),
            "meta_data": meta_data or {}
        }
        
        # Add to queue for potential streaming
        self.response_queue.append(response)
        
        return response
    
    def create_enhanced_text_response(self, user_id: int, query: str,
                                    text_content: str, 
                                    additional_components: List[UIComponent] = None) -> Dict[str, Any]:
        """Create enhanced text response with additional components"""
        text_component = UIComponentFactory.create_text_component(
            f"text_{int(datetime.now().timestamp())}", 
            text_content
        )
        
        components = [text_component]
        if additional_components:
            components.extend(additional_components)
        
        return self.create_interactive_response(user_id, query, components)
    
    def analyze_result_for_ui(self, result: Dict[str, Any]) -> List[UIComponent]:
        """Analyze a result and automatically create appropriate UI components"""
        components = []
        
        try:
            # Check if result contains structured data
            if isinstance(result, dict):
                # Create table for structured data
                if "data" in result and isinstance(result["data"], list):
                    if all(isinstance(item, dict) for item in result["data"]):
                        table_component = UIComponentFactory.create_table_component(
                            f"table_{int(datetime.now().timestamp())}",
                            result["data"]
                        )
                        table_component.title = result.get("title", "نتائج البيانات")
                        components.append(table_component)
                
                # Create chart for numerical data
                if "results" in result and isinstance(result["results"], list):
                    chart_data = self._extract_chart_data(result["results"])
                    if chart_data:
                        chart_component = UIComponentFactory.create_chart_component(
                            f"chart_{int(datetime.now().timestamp())}",
                            "bar",
                            chart_data
                        )
                        chart_component.title = result.get("title", "رسم بياني")
                        components.append(chart_component)
                
                # Create location component for coordinate data
                if "location" in result:
                    location = result["location"]
                    if isinstance(location, dict) and "lat" in location and "lng" in location:
                        map_component = UIComponentFactory.create_map_component(
                            f"map_{int(datetime.now().timestamp())}",
                            location
                        )
                        map_component.title = result.get("title", "الموقع")
                        components.append(map_component)
                
                # Create code component for code results
                if "code" in result:
                    code_component = UIComponentFactory.create_code_component(
                        f"code_{int(datetime.now().timestamp())}",
                        result["code"],
                        result.get("language", "text")
                    )
                    code_component.title = result.get("title", "الكود")
                    components.append(code_component)
            
            # Always create a text component for the main response
            text_content = self._format_result_as_text(result)
            text_component = UIComponentFactory.create_text_component(
                f"main_text_{int(datetime.now().timestamp())}",
                text_content
            )
            components.insert(0, text_component)
            
        except Exception as e:
            logger.error(f"UI component analysis error: {e}")
            # Fallback to simple text component
            text_component = UIComponentFactory.create_text_component(
                f"fallback_{int(datetime.now().timestamp())}",
                f"خطأ في تحليل النتائج: {str(e)}"
            )
            components = [text_component]
        
        return components
    
    def _extract_chart_data(self, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract chart data from results"""
        try:
            # Simple chart data extraction - look for numerical columns
            if not results:
                return None
            
            # Get all keys from first result
            first_result = results[0]
            keys = list(first_result.keys())
            
            # Find numerical columns
            numerical_columns = []
            for key in keys:
                values = [item.get(key, 0) for item in results if isinstance(item.get(key), (int, float))]
                if values and any(v != 0 for v in values):
                    numerical_columns.append(key)
            
            if not numerical_columns:
                return None
            
            # Create chart data
            chart_data = {
                "labels": [str(item.get(keys[0], "")) for item in results],
                "datasets": []
            }
            
            for col in numerical_columns[:5]:  # Limit to 5 datasets
                values = [item.get(col, 0) for item in results if isinstance(item.get(col), (int, float))]
                chart_data["datasets"].append({
                    "label": col,
                    "data": values
                })
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Chart data extraction error: {e}")
            return None
    
    def _format_result_as_text(self, result: Dict[str, Any]) -> str:
        """Format result as readable text"""
        try:
            if isinstance(result, dict):
                if "content" in result:
                    return result["content"]
                elif "message" in result:
                    return result["message"]
                elif "response" in result:
                    return result["response"]
                else:
                    return json.dumps(result, ensure_ascii=False, indent=2)
            else:
                return str(result)
        except Exception:
            return "خطأ في تنسيق النتائج"
    
    def get_response_summary(self) -> Dict[str, Any]:
        """Get summary of all responses"""
        total_responses = len(self.response_queue)
        total_components = sum(len(resp.get("components", [])) for resp in self.response_queue)
        
        component_types = {}
        for response in self.response_queue:
            for component in response.get("components", []):
                comp_type = component.get("component_type")
                component_types[comp_type] = component_types.get(comp_type, 0) + 1
        
        return {
            "total_responses": total_responses,
            "total_components": total_components,
            "component_types": component_types,
            "last_response_time": self.response_queue[-1]["timestamp"] if self.response_queue else None
        }


# Global UI component manager
ui_component_manager = UIComponentManager()


def create_enhanced_response(result: Dict[str, Any], user_id: int, query: str) -> Dict[str, Any]:
    """Create enhanced response with UI components from any result"""
    try:
        components = ui_component_manager.analyze_result_for_ui(result)
        
        response = ui_component_manager.create_interactive_response(
            user_id=user_id,
            query=query,
            components=components,
            meta_data={
                "source": "auto_ui_analysis",
                "component_count": len(components),
                "analysis_timestamp": datetime.now().isoformat()
            }
        )
        
        logger.info(f"Created enhanced response with {len(components)} UI components")
        return response
        
    except Exception as e:
        logger.error(f"Enhanced response creation error: {e}")
        # Fallback to simple text response
        return {
            "user_id": user_id,
            "query": query,
            "response_type": "text",
            "content": "خطأ في إنشاء الاستجابة المحسنة",
            "timestamp": datetime.now().isoformat()
        }