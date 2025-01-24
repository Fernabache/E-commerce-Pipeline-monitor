import numpy as np
from typing import Dict, List, Any
from src.utils.logging import setup_logger
from src.monitoring.metrics import MetricsCollector

logger = setup_logger(__name__)

class AnomalyDetector:
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.thresholds = {
            'orders': {
                'min_hourly_orders': 10,
                'max_order_value_change': 0.3,
                'min_unique_customers': 5
            },
            'transactions': {
                'max_processing_time': 30,  # seconds
                'max_failure_rate': 0.05
            },
            'inventory': {
                'max_stale_items_ratio': 0.1,
                'max_sync_delay': 300  # seconds
            }
        }

    def detect_pipeline_issues(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect anomalies in pipeline metrics"""
        anomalies = []
        
        # Check order metrics
        order_anomalies = self._check_order_anomalies(metrics.get('order_volume', {}))
        anomalies.extend(order_anomalies)
        
        # Check transaction metrics
        transaction_anomalies = self._check_transaction_anomalies(
            metrics.get('payment_processing', {})
        )
        anomalies.extend(transaction_anomalies)
        
        # Check inventory metrics
        inventory_anomalies = self._check_inventory_anomalies(
            metrics.get('inventory_updates', {})
        )
        anomalies.extend(inventory_anomalies)
        
        return anomalies

    def _check_order_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for anomalies in order metrics"""
        anomalies = []
        
        if metrics.get('order_count', 0) < self.thresholds['orders']['min_hourly_orders']:
            anomalies.append({
                'type': 'order_volume',
                'severity': 'high',
                'message': f"Order volume below threshold: {metrics.get('order_count')} orders"
            })
            
        # Check for sudden changes in average order value
        historical_avg = self._get_historical_average('orders', 'avg_order_value')
        if historical_avg:
            current_avg = metrics.get('avg_order_value', 0)
            change = abs(current_avg - historical_avg) / historical_avg
            
            if change > self.thresholds['orders']['max_order_value_change']:
                anomalies.append({
                    'type': 'order_value',
                    'severity': 'medium',
                    'message': f"Unusual change in average order value: {change:.2%}"
                })
        
        return anomalies

    def _check_transaction_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for anomalies in transaction processing"""
        anomalies = []
        
        if metrics.get('avg_processing_time', 0) > self.thresholds['transactions']['max_processing_time']:
            anomalies.append({
                'type': 'processing_time',
                'severity': 'high',
                'message': f"High transaction processing time: {metrics.get('avg_processing_time')}s"
            })
            
        total_transactions = metrics.get('failed_transactions', 0) + metrics.get('successful_transactions', 0)
        if total_transactions > 0:
            failure_rate = metrics.get('failed_transactions', 0) / total_transactions
            if failure_rate > self.thresholds['transactions']['max_failure_rate']:
                anomalies.append({
                    'type': 'transaction_failures',
                    'severity': 'critical',
                    'message': f"High transaction failure rate: {failure_rate:.2%}"
                })
        
        return anomalies

    def _check_inventory_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for anomalies in inventory synchronization"""
        anomalies = []
        
        if metrics.get('total_products', 0) > 0:
            stale_ratio = metrics.get('stale_items', 0) / metrics.get('total_products', 1)
            if stale_ratio > self.thresholds['inventory']['max_stale_items_ratio']:
                anomalies.append({
                    'type': 'inventory_sync',
                    'severity': 'medium',
                    'message': f"High ratio of stale inventory items: {stale_ratio:.2%}"
                })
        
        latest_sync = metrics.get('latest_sync')
        if latest_sync:
            sync_delay = (datetime.now() - latest_sync).total_seconds()
            if sync_delay > self.thresholds['inventory']['max_sync_delay']:
                anomalies.append({
                    'type': 'sync_delay',
                    'severity': 'high',
                    'message': f"Inventory sync delayed by {sync_delay}s"
                })
        
        return anomalies

    def _get_historical_average(self, metric_type: str, field: str) -> float:
        """Calculate historical average for a metric"""
        try:
            historical_data = self.metrics_collector.metrics_cache.get(metric_type, [])
            if not historical_data:
                return None
                
            values = [m.get(field, 0) for m in historical_data]
            return np.mean(values)
            
        except Exception as e:
            logger.error(f"Error calculating historical average: {str(e)}")
            return None
