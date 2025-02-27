from setuptools import setup, find_packages

setup(
    name="sodav-monitor-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy",
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-mock",
        "pytest-benchmark",
        "numpy",
        "librosa",
        "redis",
        "aioredis",
        "fastapi",
        "uvicorn",
        "python-multipart",
        "psutil",
        "aiohttp",
        "musicbrainzngs",
        "pydantic",
    ],
    python_requires=">=3.8",
) 