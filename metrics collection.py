from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, Any
from src.utils.logging import setup_logger

logger = setup_logger(__name__)

class MetricsCollector:
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.metrics_cache = {}

    def track_hourly_orders(self) -> Dict[str, Any]:
        """Track hourly order volume and related metrics"""
        try:
            query = """
                SELECT COUNT(*) as order_count,
                       AVG(total_amount) as avg_order_value,
                       COUNT(DISTINCT customer_id) as unique_customers
                FROM orders
                WHERE created_at >= NOW() - INTERVAL '1 HOUR'
                GROUP BY DATE_TRUNC('hour', created_at)
            """
            results = pd.read_sql(query, self.db)
            
            metrics = {
                'timestamp': datetime.now(),
                'order_count': results['order_count'].iloc[0],
                'avg_order_value': results['avg_order_value'].iloc[0],
                'unique_customers': results['unique_customers'].iloc[0]
            }
            
            self._cache_metrics('orders', metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error tracking orders: {str(e)}")
            return None

    def monitor_transaction_time(self) -> Dict[str, Any]:
        """Monitor payment processing times"""
        try:
            query = """
                SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_processing_time,
                       COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_transactions
                FROM transactions
                WHERE created_at >= NOW() - INTERVAL '1 HOUR'
            """
            results = pd.read_sql(query, self.db)
            
            metrics = {
                'timestamp': datetime.now(),
                'avg_processing_time': results['avg_processing_time'].iloc[0],
                'failed_transactions': results['failed_transactions'].iloc[0]
            }
            
            self._cache_metrics('transactions', metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error monitoring transactions: {str(e)}")
            return None

    def check_stock_sync(self) -> Dict[str, Any]:
        """Check inventory synchronization status"""
        try:
            query = """
                SELECT COUNT(*) as total_products,
                       COUNT(CASE WHEN last_sync < NOW() - INTERVAL '5 MINUTE' THEN 1 END) as stale_items,
                       MAX(last_sync) as latest_sync
                FROM inventory_status
            """
            results = pd.read_sql(query, self.db)
            
            metrics = {
                'timestamp': datetime.now(),
                'total_products': results['total_products'].iloc[0],
                'stale_items': results['stale_items'].iloc[0],
                'latest_sync': results['latest_sync'].iloc[0]
            }
            
            self._cache_metrics('inventory', metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error checking inventory sync: {str(e)}")
            return None

    def _cache_metrics(self, metric_type: str, metrics: Dict[str, Any]):
        """Cache metrics for anomaly detection"""
        if metric_type not in self.metrics_cache:
            self.metrics_cache[metric_type] = []
        
        self.metrics_cache[metric_type].append(metrics)
        
        # Keep last 24 hours of metrics
        cutoff = datetime.now() - timedelta(hours=24)
        self.metrics_cache[metric_type] = [
            m for m in self.metrics_cache[metric_type] 
            if m['timestamp'] > cutoff
        ]
