# scrapers_config.py - Scraper Platform configuration registry

SCRAPER_CONFIG = {
    "apsc": {
        "frequency": "6h",
        "timeout": 30,
        "priority": "high",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "slprb": {
        "frequency": "6h",
        "timeout": 30,
        "priority": "high",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "dibrugarh": {
        "frequency": "12h",
        "timeout": 30,
        "priority": "medium",
        "category": "mixed",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "gauhati": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "medium",
        "category": "mixed",
        "rate_limit": {
            "delay_seconds": 3.0,
            "jitter": True,
        }
    },
    "cotton": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "medium",
        "category": "mixed",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "assam_career": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 3.0,
            "jitter": True,
        }
    },
    "daily_assam_job": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 3.0,
            "jitter": True,
        }
    },
    "nhm_assam": {
        "frequency": "12h",
        "timeout": 30,
        "priority": "medium",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "aesrb": {
        "frequency": "12h",
        "timeout": 30,
        "priority": "medium",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "ncs_portal": {
        "frequency": "24h",
        "timeout": 45,
        "priority": "low",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 4.0,
            "jitter": True,
        }
    },
    "tezpur": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "medium",
        "category": "mixed",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "bodoland": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "medium",
        "category": "mixed",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "mangaldai": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "ahsec": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "seba": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    # Phase 1A Scrapers
    "assam_university": {
        "frequency": "12h",
        "timeout": 30,
        "priority": "medium",
        "category": "mixed",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "astu": {
        "frequency": "12h",
        "timeout": 30,
        "priority": "medium",
        "category": "mixed",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    # Phase 1B Scrapers
    "ghc": {
        "frequency": "6h",
        "timeout": 30,
        "priority": "high",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    # Phase 1C Scrapers
    "all_job_assam": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 3.0,
            "jitter": True,
        }
    },
    # Batch 2 Scrapers
    "kkhsou": {
        "frequency": "12h",
        "timeout": 30,
        "priority": "medium",
        "category": "mixed",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "awu": {
        "frequency": "12h",
        "timeout": 30,
        "priority": "medium",
        "category": "mixed",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "nrl": {
        "frequency": "12h",
        "timeout": 30,
        "priority": "medium",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 3.0,
            "jitter": True,
        }
    },
    "assam_job_news": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "jobs",
        "rate_limit": {
            "delay_seconds": 3.0,
            "jitter": True,
        }
    },
    "darrang_college": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "tezpur_college": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "lokd_college": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "royal_global": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "ignou_guwahati": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "don_bosco": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "pandu_college": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "adtu": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    },
    "dhe_assam": {
        "frequency": "24h",
        "timeout": 30,
        "priority": "low",
        "category": "academic",
        "rate_limit": {
            "delay_seconds": 2.0,
            "jitter": True,
        }
    }
}
