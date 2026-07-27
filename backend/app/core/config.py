from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "SentraScan"

    DATABASE_URL: str = "postgresql+psycopg2://sentrascan:sentrascan@db:5432/sentrascan"
    REDIS_URL: str = "redis://redis:6379/0"

    # true yapilirsa taramalar Celery kuyruguna gonderilmez, API isteginin
    # icinde senkron calisir. Redis ve ayri bir worker gerekmedigi icin
    # Docker'siz yerel demo/gelistirme kolaylasir. Tarama bitene kadar
    # istek bekledigi icin gercek kullanimda false kalmalidir.
    CELERY_TASK_ALWAYS_EAGER: bool = False

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # AI rapor/chat katmani yerel Ollama sunucusu uzerinden calisir; API
    # anahtari gerekmez ve bulgular makineden disari cikmaz. Ollama'ya
    # ulasilamazsa sistem kural tabanli fallback rapora duser.
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    # Yerel CPU cikarimi yavas olabildigi icin genis tutuldu (saniye).
    OLLAMA_TIMEOUT: int = 300

    VERIFICATION_TXT_PREFIX: str = "_sentrascan-verify"
    # DEV ONLY: skips the real DNS TXT ownership check so the scan flow can
    # be demoed without owning a domain. Never enable this on a shared or
    # production deployment - it lets any authenticated user "verify" and
    # scan any domain.
    SKIP_TARGET_VERIFICATION: bool = False

    # Recon module tuning
    RECON_PORT_LIST: list[int] = [21, 22, 25, 80, 110, 143, 443, 3306, 3389, 5432, 6379, 8080, 8443]
    RECON_PORT_TIMEOUT: float = 1.5
    RECON_MAX_SUBDOMAINS: int = 50


settings = Settings()
