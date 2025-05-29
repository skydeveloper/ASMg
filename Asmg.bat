@echo off
REM Скрипт за създаване на структурата на проекта ASMg

REM Създаване на основната папка на проекта
IF NOT EXIST ASMg (
    ECHO Creating project directory: ASMg
    mkdir ASMg
) ELSE (
    ECHO Directory ASMg already exists.
)
cd ASMg

REM --- Създаване на Backend структурата ---
ECHO Creating backend directories...
IF NOT EXIST backend mkdir backend
cd backend

IF NOT EXIST api mkdir api
IF NOT EXIST services mkdir services
IF NOT EXIST translations mkdir translations
IF NOT EXIST utils mkdir utils

ECHO Creating backend files...
type NUL > __init__.py
type NUL > app.py
type NUL > config.py

cd api
type NUL > __init__.py
type NUL > operator_routes.py
type NUL > travel_lot.py
type NUL > machine_status.py
cd ..

cd services
type NUL > __init__.py
type NUL > com_port_manager.py
type NUL > data_simulator.py
type NUL > opc_ua_client.py
cd ..

cd translations
type NUL > __init__.py
type NUL > translation_manager.py
type NUL > bg.json
type NUL > en.json
type NUL > sr.json
cd ..

cd utils
type NUL > __init__.py
type NUL > logger.py
cd ..

cd ..
REM --- Край на Backend структурата ---

REM --- Създаване на templates структурата (за Jinja2) ---
ECHO Creating templates directory...
IF NOT EXIST templates mkdir templates
cd templates

ECHO Creating template files...
type NUL > index.html

cd ..
REM --- Край на templates структурата ---

REM --- Създаване на static структурата (за CSS, JS, изображения) ---
ECHO Creating static directories...
IF NOT EXIST static mkdir static
cd static

IF NOT EXIST css mkdir css
IF NOT EXIST js mkdir js
IF NOT EXIST img mkdir img

cd css
ECHO Creating static CSS files...
type NUL > style.css
cd ..

cd js
ECHO Creating static JS files...
type NUL > main_app.js
cd ..

cd ..
REM --- Край на static структурата ---

REM --- Създаване на файлове в коренната директория на проекта ---
ECHO Creating root project files...
type NUL > .gitignore
type NUL > README.md
type NUL > requirements.txt
type NUL > run.py

cd ..
ECHO Project structure for ASMg created successfully!
pause