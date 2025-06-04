document.addEventListener('DOMContentLoaded', function () {
    console.log('[JS] DOMContentLoaded - Финална синхронизирана версия заредена.');

    const socket = io(window.location.origin);
    const langSelect = document.getElementById('language-select');
    const taskTitle = document.getElementById('task-title');
    const taskInstruction = document.getElementById('task-instruction');
    const operatorIdDisplay = document.getElementById('operator-id-display');
    const operatorNameDisplay = document.getElementById('operator-name-display');
    const logoutBtn = document.getElementById('logout-btn');
    const travelLotIdDisplay = document.getElementById('travel-lot-id-display');
    const productNumberDisplay = document.getElementById('product-number-display');
    const logPanel = document.getElementById('log-panel');
    const overallStatusIndicator = document.getElementById('overall-status-indicator');
    const overallStatusText = document.getElementById('overall-status-text');

    let state = {
        currentStep: 'awaiting_operator',
        operator: null,
        travelLot: null,
        translations: {}
    };

    function getTranslation(key) {
        if (!key || typeof key !== 'string') return key || '';
        const keys = key.split('.');
        let result = state.translations;
        for (const k of keys) {
            if (result && typeof result === 'object' && k in result) {
                result = result[k];
            } else {
                return key;
            }
        }
        return typeof result === 'string' ? result : key;
    }

    function updateUI() {
        if (taskTitle) taskTitle.textContent = getTranslation(state.currentStep === 'awaiting_operator' ? 'task.scanOperator' : state.currentStep === 'awaiting_travel_lot' ? 'task.scanTravelLot' : 'task.ready');
        if (taskInstruction) {
            if (state.currentStep === 'awaiting_operator') taskInstruction.textContent = getTranslation('task.waitingForScan');
            else if (state.currentStep === 'awaiting_travel_lot' && state.operator) taskInstruction.innerHTML = `${getTranslation('task.operatorIdentified')}: <strong>${state.operator.name}</strong>. ${getTranslation('task.scanTravelLotPrompt')}`;
            else if (state.currentStep === 'ready') taskInstruction.textContent = getTranslation('task.systemReadyPrompt');
        }
        if (operatorIdDisplay) operatorIdDisplay.textContent = state.operator ? state.operator.id : '--';
        if (operatorNameDisplay) operatorNameDisplay.textContent = state.operator ? state.operator.name : getTranslation('operatorSection.nameDefault');
        if (travelLotIdDisplay) travelLotIdDisplay.textContent = state.travelLot ? state.travelLot.id : '--';
        if (productNumberDisplay) productNumberDisplay.textContent = state.travelLot ? state.travelLot.productNumber : '--';
        if (logoutBtn) logoutBtn.style.display = state.operator ? 'block' : 'none';
    }

    function addLogEntry(message, level = 'info') {
        if (!logPanel) return;
        let displayMessage = message;
        if (message && typeof message === 'string' && !message.includes('{') && !message.includes('}')) {
            displayMessage = getTranslation(message);
        }
        const entryDiv = document.createElement('div');
        entryDiv.classList.add('log-entry', `log-${level}`);
        const timestamp = new Date().toLocaleTimeString('bg-BG');
        entryDiv.innerHTML = `<span class="text-gray-500 mr-2">${timestamp}</span> &raquo; <span class="ml-1">${displayMessage}</span>`;
        logPanel.insertBefore(entryDiv, logPanel.firstChild);
    }

    function applyStaticTranslations() {
        document.querySelectorAll('[data-translate-key]').forEach(element => {
            const key = element.getAttribute('data-translate-key');
            // Тези се управляват от updateUI или handleStatusUpdate
            if (element.id !== 'task-title' &&
                element.id !== 'task-instruction' &&
                element.id !== 'operator-name-display' &&
                element.id !== 'overall-status-text' &&
                !element.id.includes('-status-text') &&
                !element.id.includes('-module-id') &&
                !element.id.includes('-module-ids') &&
                element.tagName !== 'TITLE') {
                element.textContent = getTranslation(key);
            } else if (element.tagName === 'TITLE') {
                 document.title = getTranslation(key); // Заглавието на страницата
            }
        });
    }

    function handleStatusUpdate(lineData) {
        if (!lineData) return;
        if (overallStatusIndicator && overallStatusText && lineData.overall_status) {
            const statusClass = (lineData.overall_status.split('.')[1] || 'idle').toLowerCase();
            overallStatusIndicator.className = 'status-indicator ' + statusClass;
            overallStatusText.textContent = getTranslation(lineData.overall_status);
            overallStatusText.setAttribute('data-translate-key', lineData.overall_status);
        }
        if (lineData.robots) {
            for (let i = 1; i <= 3; i++) {
                const robotStatusIndicator = document.getElementById(`robot${i}-status-indicator`);
                const robotStatusText = document.getElementById(`robot${i}-status-text`);
                if (robotStatusIndicator && robotStatusText && lineData.robots[i] && lineData.robots[i].status) {
                    const statusClass = (lineData.robots[i].status.split('.')[1] || 'idle').toLowerCase();
                    robotStatusIndicator.className = 'status-indicator ' + statusClass;
                    robotStatusText.textContent = getTranslation(lineData.robots[i].status);
                    robotStatusText.setAttribute('data-translate-key', lineData.robots[i].status);
                }
            }
        }
        if (lineData.turntable1) {
            for (let i = 1; i <= 4; i++) {
                const moduleIdSpan = document.getElementById(`v1p${i}-module-id`);
                const statusTextSpan = document.getElementById(`v1p${i}-status-text`);
                if (lineData.turntable1[i]) {
                    if (moduleIdSpan) moduleIdSpan.textContent = lineData.turntable1[i].moduleId || '--';
                    if (statusTextSpan) {
                        statusTextSpan.textContent = getTranslation(lineData.turntable1[i].status || 'status.idle');
                        statusTextSpan.setAttribute('data-translate-key', lineData.turntable1[i].status || 'status.idle');
                    }
                }
            }
        }
        if (lineData.turntable2) {
            for (let i = 1; i <= 4; i++) {
                const moduleIdsSpan = document.getElementById(`v2p${i}-module-ids`);
                const statusTextSpan = document.getElementById(`v2p${i}-status-text`);
                if (lineData.turntable2[i]) {
                    if (moduleIdsSpan) moduleIdsSpan.textContent = (lineData.turntable2[i].moduleIds || []).join(', ') || '--';
                    if (statusTextSpan) {
                         statusTextSpan.textContent = getTranslation(lineData.turntable2[i].status || 'status.idle');
                         statusTextSpan.setAttribute('data-translate-key', lineData.turntable2[i].status || 'status.idle');
                    }
                }
            }
        }
         if (lineData.trays) {
             const trayInIndicator = document.getElementById('tray-in-status-indicator');
             const trayInText = document.getElementById('tray-in-status-text');
             if(trayInIndicator && trayInText && lineData.trays.in && lineData.trays.in.status){
                trayInIndicator.className = 'status-indicator ' + (lineData.trays.in.status.split('.')[1] || 'empty');
                trayInText.textContent = getTranslation(lineData.trays.in.status);
                trayInText.setAttribute('data-translate-key', lineData.trays.in.status);
             }
             const trayOutIndicator = document.getElementById('tray-out-status-indicator');
             const trayOutText = document.getElementById('tray-out-status-text');
             if(trayOutIndicator && trayOutText && lineData.trays.out && lineData.trays.out.status){
                trayOutIndicator.className = 'status-indicator ' + (lineData.trays.out.status.split('.')[1] || 'empty');
                trayOutText.textContent = getTranslation(lineData.trays.out.status);
                trayOutText.setAttribute('data-translate-key', lineData.trays.out.status);
             }
        }
    }

    socket.on('connect', () => {
        console.log('Успешно свързан към сървъра.');
        socket.emit('request_initial_data');
    });

    socket.on('initial_data', (data) => {
        console.log('Получени начални данни от сървъра:', data);
        if (data.translations) {
            state.translations = data.translations;
            console.log('Преводите са заредени в state.translations.');
        } else {
            console.warn('Не са получени преводи в initial_data!');
        }

        applyStaticTranslations();

        if (data.line_status) {
            console.log('Получен е line_status, прилагам го...');
            handleStatusUpdate(data.line_status);
        } else {
            console.warn('Не е получен line_status в initial_data!');
        }
        updateUI();
    });

    socket.on('update_status', handleStatusUpdate);

    socket.on('barcode_scanned', (data) => {
        const barcode = data.barcode;
        addLogEntry(`log.barcodeReceived`, 'info', {barcodeData: barcode}); // Подаваме като ключ
        if (state.currentStep === 'awaiting_operator') {
            if(taskInstruction) taskInstruction.textContent = getTranslation('log.validatingOperator').replace('{badge_id}', barcode);
            socket.emit('validate_operator', { 'barcode': barcode });
        } else if (state.currentStep === 'awaiting_travel_lot') {
            if(taskInstruction) taskInstruction.textContent = `Проверка на маршрутна карта: ${barcode}...`;
            socket.emit('validate_travel_lot', { 'barcode': barcode });
        }
    });

    socket.on('operator_validation_result', (data) => {
        console.log('[JS] operator_validation_result:', data);
        let scannedValue = 'N/A'; // За логване, ако data.operator_info е null
        if (state.currentStep === 'awaiting_operator') { // Опитваме се да вземем сканирания баркод
            try { // Добавяме try-catch, ако taskInstruction.textContent е неочакван
                scannedValue = taskInstruction.textContent.split(': ')[1].replace('...','');
            } catch(e) { console.warn("Не може да се извлече сканиран баркод от taskInstruction"); }
        }

        if (data.is_valid && data.operator_info) {
            state.operator = data.operator_info;
            state.currentStep = 'awaiting_travel_lot';
            addLogEntry("log.operatorLoggedIn", 'success', {operator_name: data.operator_info.name});
        } else {
            state.operator = null;
            state.currentStep = 'awaiting_operator';
            addLogEntry("log.operatorScanFailed", 'error', {operator_id: data.operator_info ? data.operator_info.id : scannedValue});
        }
        updateUI();
    });

    socket.on('travel_lot_validation_result', (data) => {
        console.log('[JS] travel_lot_validation_result:', data);
        if (data.is_valid && data.travel_lot_info) {
            state.travelLot = data.travel_lot_info;
            state.currentStep = 'ready';
            addLogEntry("log.travelLotIdentified", 'success', {lot_id: data.travel_lot_info.id, item_number: data.travel_lot_info.productNumber});
        } else {
             addLogEntry("log.travelLotApiError", 'error', {error: data.error || 'Невалидна пътна карта'});
        }
        updateUI();
    });

    socket.on('log_message', (log) => { // Тези съобщения идват вече преведени от сървъра
        addLogEntry(log.message, log.level);
    });

    socket.on('disconnect', () => addLogEntry('socket.disconnected', 'error')); // Използваме ключ

    if (langSelect) {
        langSelect.addEventListener('change', function() {
            window.location.href = `/set_language/${this.value}`;
        });
    }
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            addLogEntry('log.operatorLoggedOut', 'info');
            socket.emit('logout_request');
        });
    }
});