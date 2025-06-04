# ASMg - Production Line Control Center

Това е уеб-базирано приложение за мониторинг и контрол на производствена линия, разработено с Flask, Socket.IO и Jinja2.

## Изисквания

* Python 3.8+
* pip

## Инсталация

1.  Клонирайте репозиторито (или създайте файловете ръчно):
    ```bash
    git clone <your-repo-url> ASMg
    cd ASMg
    ```

2.  Създайте и активирайте виртуална среда (препоръчително):
    ```bash
    python -m venv .venv
    # За Windows
    .\.venv\Scripts\activate
    # За Linux/macOS
    # source .venv/bin/activate
    ```

3.셔 Инсталирайте зависимостите:
    ```bash
    pip install -r requirements.txt
    ```

## Конфигурация

Конфигурационните настройки се намират във файла `backend/config.py`. Можете да промените:
* `BARCODE_SCANNER_PORT`: COM портът за баркод скенера (напр. 'COM4').
* `OPCUA_SERVER_URL`: URL на OPC UA сървъра (за бъдеща интеграция).
* `DEBUG`: `True` за режим на разработка, `False` за продукция.
* `PORT`, `HOST`: Порт и хост, на които да слуша сървърът.
* `SUPPORTED_LANGUAGES`, `DEFAULT_LANGUAGE`: За многоезичност.

## Стартиране на приложението

От коренната директория на проекта (`ASMg/`):
```bash
python run.py