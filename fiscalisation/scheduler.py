# fiscalisation/scheduler.py
import logging
import threading

logger = logging.getLogger(__name__)

_scheduler_running = False
_sync_thread = None


def start_background_sync(interval_seconds: int = 30):
    global _scheduler_running, _sync_thread
    
    if _scheduler_running:
        return
    
    def sync_worker():
        import time
        from fiscalisation.services import FiscalisationService
        
        while _scheduler_running:
            try:
                time.sleep(interval_seconds)
                service = FiscalisationService()
                if service.is_fiscalisation_active():
                    pending_count = service.get_pending_count()
                    if pending_count > 0:
                        logger.info(f"Background sync: {pending_count} pending receipts found")
                        results = service.sync_pending_receipts(limit=50)
                        if results['total'] > 0:
                            logger.info(f"Background sync: {results['success']} synced, {results['failed']} failed")
            except Exception as e:
                logger.exception(f"Background sync error: {e}")
    
    _scheduler_running = True
    _sync_thread = threading.Thread(target=sync_worker, daemon=True)
    _sync_thread.start()
    logger.info(f"Background sync started (interval: {interval_seconds}s)")


def stop_background_sync():
    global _scheduler_running
    _scheduler_running = False