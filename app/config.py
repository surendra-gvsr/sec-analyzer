from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llama_cloud_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama3-8b-8192"

    sec_user_email: str = "demo@sec-analyzer.com"
    sec_company_name: str = "SECAnalyzerDemo"

    target_tickers: str = "AAPL,MSFT"
    target_years: str = "2021,2022,2023,2024"

    pinecone_api_key: str = ""
    pinecone_index_name: str = "sec-filings"

    raw_filings_dir: str = "data/raw_filings"
    parsed_markdown_dir: str = "data/parsed_markdown"
    graph_store_dir: str = "data/graph_store"

    environment: str = "development"
    log_level: str = "INFO"

    @property
    def tickers_list(self) -> List[str]:
        return [t.strip().upper() for t in self.target_tickers.split(",") if t.strip()]

    @property
    def years_list(self) -> List[int]:
        return [int(y.strip()) for y in self.target_years.split(",") if y.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def graph_store_path(self) -> str:
        return os.path.join(self.graph_store_dir, "property_graph.json")

    @property
    def benchmark_results_path(self) -> str:
        return "data/benchmark_results.json"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
