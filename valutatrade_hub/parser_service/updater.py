from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import parser_logger
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Класс для обновления курсов валют"""
    
    def __init__(self, config: ParserConfig = None):
        """Инициализирует обновлятель курсов валют"""
        self.config = config or ParserConfig()
        self.storage = RatesStorage(self.config)
        self.clients = {
            "coingecko": CoinGeckoClient(self.config),
            "exchangerate": ExchangeRateApiClient(self.config)
        }
    
    def run_update(self, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """Запускает обновление курсов валют"""
        if sources is None:
            sources = list(self.clients.keys())
        parser_logger.info("Starting rates update...")
        
        all_rates = {}
        update_stats = {
            "total_rates": 0,
            "sources_updated": [],
            "sources_failed": [],
            "errors": [],
            "last_refresh": None
        }
        
        for source_name in sources:
            if source_name not in self.clients:
                error_msg = f"Unknown source: {source_name}"
                parser_logger.error(error_msg)
                update_stats["errors"].append(error_msg)
                update_stats["sources_failed"].append(source_name)
                continue
            client_name = ("CoinGecko" if source_name == "coingecko" 
                        else "ExchangeRate-API")
            try:
                client = self.clients[source_name]
                parser_logger.info(f"Fetching from {client_name}...")
                rates = client.fetch_rates()
                if rates:
                    for pair, rate in rates.items():
                        meta = {
                            "raw_id": (self.config.CRYPTO_ID_MAP
                            .get(pair.split('_')[0], "")),
                            "status_code": 200,
                            "request_timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        record = self.storage.create_historical_record(pair, rate, 
                                                                    client_name, meta)
                        self.storage.save_historical_record(record)
                    all_rates.update(rates)
                    update_stats["sources_updated"].append(source_name)
                    parser_logger.info(f"Fetching from {client_name}..."
                                f"OK ({len(rates)} rates)")
                else:
                    error_msg = f"No rates received from {client_name}"
                    parser_logger.warning(error_msg)
                    update_stats["errors"].append(error_msg)
                    update_stats["sources_failed"].append(source_name)
                
            except ApiRequestError as e:
                error_msg = f"Failed to fetch from {client_name}: {str(e)}"
                parser_logger.error(error_msg)
                update_stats["errors"].append(error_msg)
                update_stats["sources_failed"].append(source_name)
            except Exception as e:
                error_msg = f"Unexpected error from {client_name}: {str(e)}"
                parser_logger.error(error_msg)
                update_stats["errors"].append(error_msg)
                update_stats["sources_failed"].append(source_name)
        
        if all_rates:
            current_time = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            rates_data = {
                "pairs": {},
                "last_refresh": current_time
            }
            for pair, rate in all_rates.items():
                source = ("CoinGecko" if pair.split('_')[0] in 
                        self.config.CRYPTO_CURRENCIES else "ExchangeRate-API")
                rates_data["pairs"][pair] = {
                    "rate": rate,
                    "updated_at": current_time,
                    "source": source
                }
            self.storage.save_current_rates(rates_data)
            update_stats["total_rates"] = len(all_rates)
            update_stats["last_refresh"] = current_time
            parser_logger.info(f"Writing {len(all_rates)} rates to data/rates.json...")
        
        return update_stats