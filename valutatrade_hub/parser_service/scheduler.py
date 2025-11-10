import threading
from typing import Optional

from valutatrade_hub.logging_config import parser_logger
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.updater import RatesUpdater


class RatesScheduler:
    """Планировщик периодического обновления курсов"""
    
    def __init__(self, config: ParserConfig = None):
        """Инициализирует планировщик обновления курсов"""
        self.config = config or ParserConfig()
        self.updater = RatesUpdater(self.config)
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self, interval_minutes: int = None):
        """Запускает периодическое обновление курсов"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            parser_logger.warning("Scheduler is already running")
            return
        
        interval = interval_minutes or self.config.UPDATE_INTERVAL_MINUTES
        self._stop_event.clear()
        
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(interval,),
            daemon=True,
            name="RatesScheduler"
        )
        self._scheduler_thread.start()
        parser_logger.info(f"Scheduler started with {interval} minute interval")
    
    def stop(self):
        """Останавливает планировщик"""
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        parser_logger.info("Scheduler stopped")
    
    def _scheduler_loop(self, interval_minutes: int):
        """Основной цикл планировщика"""
        interval_seconds = interval_minutes * 60
        while not self._stop_event.is_set():
            try:
                parser_logger.info("Scheduled rates update started")
                stats = self.updater.run_update()
                if stats["sources_failed"]:
                    parser_logger.warning(f"Scheduled update completed with errors:"
                                f"{stats['errors']}")
                else:
                    parser_logger.info(f"Scheduled update completed successfully: "
                                f"{stats['total_rates']} rates updated")  
            except Exception as e:
                parser_logger.error(f"Scheduled update failed: {str(e)}")
                self._stop_event.wait(interval_seconds)
    
    def run_once(self):
        """Запускает однократное обновление курсов"""
        parser_logger.info("Manual rates update started")
        return self.updater.run_update()