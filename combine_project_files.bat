@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Името на файла, в който ще се събира всичко
SET OUTPUT_FILE=ASMg_Project_Source_Code.txt
REM Изтриваме стария файл, ако съществува, за да започнем на чисто
IF EXIST "%OUTPUT_FILE%" DEL "%OUTPUT_FILE%"

ECHO Събиране на файловете в %OUTPUT_FILE%...
ECHO.

REM Функция за добавяне на съдържанието на файл към OUTPUT_FILE
REM Добавя и маркер с името на файла преди съдържанието му
:AddFileContent
ECHO Processing: %~1 >> "%OUTPUT_FILE%"
ECHO --- START FILE: %~1 --- >> "%OUTPUT_FILE%"
ECHO. >> "%OUTPUT_FILE%"
type "%~1" >> "%OUTPUT_FILE%"
ECHO. >> "%OUTPUT_FILE%"
ECHO --- END FILE: %~1 --- >> "%OUTPUT_FILE%"
ECHO. >> "%OUTPUT_FILE%"
ECHO Added: %~1
GOTO :EOF

REM Главни файлове в коренната директория
CALL :AddFileContent ".gitignore"
CALL :AddFileContent "README.md"
CALL :AddFileContent "requirements.txt"
CALL :AddFileContent "run.py"
CALL :AddFileContent "Asmg.bat"

REM Файлове в backend/
CALL :AddFileContent "backend\__init__.py"
CALL :AddFileContent "backend\app.py"
CALL :AddFileContent "backend\config.py"

REM Файлове в backend/api/
CALL :AddFileContent "backend\api\__init__.py"
CALL :AddFileContent "backend\api\machine_status.py"
CALL :AddFileContent "backend\api\operator_routes.py"
CALL :AddFileContent "backend\api\travel_lot.py"

REM Файлове в backend/services/
CALL :AddFileContent "backend\services\__init__.py"
CALL :AddFileContent "backend\services\com_port_manager.py"
CALL :AddFileContent "backend\services\data_simulator.py"
CALL :AddFileContent "backend\services\opc_ua_client.py"
CALL :AddFileContent "backend\services\traceability_api.py"

REM Файлове в backend/translations/
CALL :AddFileContent "backend\translations\__init__.py"
CALL :AddFileContent "backend\translations\translation_manager.py"
CALL :AddFileContent "backend\translations\bg.json"
CALL :AddFileContent "backend\translations\en.json"
CALL :AddFileContent "backend\translations\sr.json"

REM Файлове в backend/utils/
CALL :AddFileContent "backend\utils\__init__.py"
CALL :AddFileContent "backend\utils\logger.py"

REM Файлове в templates/
CALL :AddFileContent "templates\index.html"

REM Файлове в static/css/
CALL :AddFileContent "static\css\style.css"

REM Файлове в static/js/
CALL :AddFileContent "static\js\main_app.js"

REM Файлове в static/img/ (ако има текстови файлове там, но обикновено са бинарни)
REM CALL :AddFileContent "static\img\logo_placeholder.png" (това е бинарен файл, няма смисъл да се добавя така)

ECHO.
ECHO Готово! Всички файлове са събрани в "%OUTPUT_FILE%"
ECHO Моля, изпратете ми съдържанието на този файл.

ENDLOCAL
pause