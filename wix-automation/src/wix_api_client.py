import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class WixAnalyticsClient:
    def __init__(self, site_id: str, config_path: str = 'config/wix_config.json'):
        self.site_id = site_id
        self.config = self._load_config(config_path)
        self.base_url = "https://www.wixapis.com/analytics/v1"
        self.session = requests.Session()
        self._setup_logging()
        self._setup_authentication()
    
    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/wix_api.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_authentication(self):
        """Configure API authentication using API Key or OAuth token"""
        api_key = os.getenv('WIX_API_KEY')
        oauth_token = os.getenv('WIX_OAUTH_TOKEN')
        
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}',
                'wix-site-id': self.site_id,
                'Content-Type': 'application/json'
            })
            self.logger.info("Configured API Key authentication")
        elif oauth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {oauth_token}',
                'Content-Type': 'application/json'
            })
            self.logger.info("Configured OAuth authentication")
        else:
            raise ValueError("Either WIX_API_KEY or WIX_OAUTH_TOKEN must be provided")
    
    def get_analytics_data(self, 
                          start_date: str, 
                          end_date: str, 
                          measurement_types: List[str] = None) -> Dict:
        """
        Retrieve analytics data for specified date range and measurement types
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format  
            measurement_types: List of measurement types (sessions, sales, orders, contacts)
        """
        if measurement_types is None:
            measurement_types = ['sessions', 'sales', 'orders', 'contacts']
        
        params = {
            'startDate': start_date,
            'endDate': end_date,
            'measurementTypes': measurement_types
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/data",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            self.logger.info(f"Retrieved analytics data from {start_date} to {end_date}")
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to retrieve analytics data: {e}")
            raise
    
    def get_recent_data(self, days_back: int = 7) -> Dict:
        """Retrieve analytics data for the past N days"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        return self.get_analytics_data(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
    
    def get_traffic_summary(self, days_back: int = 30) -> Dict:
        """Generate comprehensive traffic summary for specified period"""
        data = self.get_recent_data(days_back)
        
        summary = {
            'collection_date': datetime.now().isoformat(),
            'period_days': days_back,
            'data_source': 'wix_analytics_api',
            'metrics': {}
        }
        
        # Process each measurement type
        for measurement in data.get('measurements', []):
            measurement_type = measurement.get('type')
            values = measurement.get('values', [])
            
            summary['metrics'][measurement_type] = {
                'total': sum(v.get('value', 0) for v in values),
                'daily_average': sum(v.get('value', 0) for v in values) / len(values) if values else 0,
                'data_points': len(values),
                'date_range': {
                    'start': values[0].get('date') if values else None,
                    'end': values[-1].get('date') if values else None
                }
            }
        
        return summary