# backend/services/opc_ua_client.py

# Placeholder за OPC UA клиент
# Трябва да инсталирате asyncua или подобна библиотека: pip install asyncua

# from asyncua import Client, ua

class OpcUaManager:
    def __init__(self, url, namespace, socketio, line_status_data, translations):
        self.url = url
        self.namespace_idx = None  # Ще се определи след свързване
        self.namespace_uri = namespace
        self.client = None
        self.socketio = socketio
        self.line_status_data = line_status_data
        self.translations = translations
        self.running = False
        self.subscription = None
        self.handler = None
        # Импортираме add_log_message тук
        from backend.app import add_log_message
        self.add_log_message = add_log_message

    async def connect(self):
        """Свързва се с OPC UA сървъра."""
        try:
            self.client = Client(url=self.url)
            await self.client.connect()
            self.namespace_idx = await self.client.get_namespace_index(self.namespace_uri)
            self.add_log_message("opcua.connected", "success", url=self.url)
            print(f"Connected to OPC UA server at {self.url}")
            self.running = True
            # Тук можете да стартирате абонамент за промени
            # await self.subscribe_to_variables()
        except Exception as e:
            self.add_log_message("opcua.connectError", "error", url=self.url, error=str(e))
            print(f"Error connecting to OPC UA server: {e}")
            self.client = None

    async def disconnect(self):
        """Прекъсва връзката с OPC UA сървъра."""
        if self.client and self.client.uaclient:
            try:
                if self.subscription:
                    await self.subscription.delete()
                    self.add_log_message("opcua.subscriptionDeleted", "info")
                await self.client.disconnect()
                self.add_log_message("opcua.disconnected", "info")
                print("Disconnected from OPC UA server.")
            except Exception as e:
                self.add_log_message("opcua.disconnectError", "error", error=str(e))
                print(f"Error disconnecting from OPC UA server: {e}")
        self.running = False
        self.client = None

    async def read_value(self, node_id_str):
        """Чете стойност от OPC UA нод."""
        if not self.client or not self.running:
            self.add_log_message("opcua.notConnectedRead", "warning", node_id=node_id_str)
            return None
        try:
            node = self.client.get_node(f"ns={self.namespace_idx};s={node_id_str}")
            value = await node.get_value()
            self.add_log_message("opcua.readValueSuccess", "debug", node_id=node_id_str, value=value)
            return value
        except Exception as e:
            self.add_log_message("opcua.readValueFail", "error", node_id=node_id_str, error=str(e))
            print(f"Error reading OPC UA node {node_id_str}: {e}")
            return None

    async def write_value(self, node_id_str, value, ua_type):
        """Записва стойност в OPC UA нод."""
        if not self.client or not self.running:
            self.add_log_message("opcua.notConnectedWrite", "warning", node_id=node_id_str)
            return False
        try:
            node = self.client.get_node(f"ns={self.namespace_idx};s={node_id_str}")
            ua_value = ua.DataValue(ua.Variant(value, ua_type))
            await node.set_value(ua_value)
            self.add_log_message("opcua.writeValueSuccess", "debug", node_id=node_id_str, value=value)
            return True
        except Exception as e:
            self.add_log_message("opcua.writeValueFail", "error", node_id=node_id_str, error=str(e))
            print(f"Error writing OPC UA node {node_id_str}: {e}")
            return False

    # Пример за абонамент (ще трябва да се адаптира според вашите нужди)
    # async def subscribe_to_variables(self):
    #     class SubHandler:
    #         def __init__(self, socketio, line_status_data, translations, add_log_message_func):
    #             self.socketio = socketio
    #             self.line_status_data = line_status_data
    #             self.translations = translations
    #             self.add_log_message = add_log_message_func

    #         def datachange_notification(self, node, val, data):
    #             node_str = node.nodeid.to_string()
    #             print(f"OPC UA DataChange: Node={node_str}, Value={val}")
    #             self.add_log_message("opcua.dataChange", "debug", node=node_str, value=val)
    #             # Тук трябва да има логика за актуализиране на self.line_status_data
    #             # и изпращане на socketio.emit('update_status', self.line_status_data)
    #             # Пример:
    #             # if "Robot1.Status" in node_str:
    #             #     self.line_status_data["robots"]["1"]["status"] = "status.working" if val else "status.idle"
    #             #     self.socketio.emit('update_status', {'robots': {'1': self.line_status_data["robots"]["1"]}})

    #     self.handler = SubHandler(self.socketio, self.line_status_data, self.translations, self.add_log_message)
    #     self.subscription = await self.client.create_subscription(500, self.handler) # Период 500ms

    #     # Примерни нодове за абонамент (трябва да се заменят с реални)
    #     nodes_to_subscribe = [
    #         # f"ns={self.namespace_idx};s=Path.To.Robot1.Status",
    #         # f"ns={self.namespace_idx};s=Path.To.Turntable1.Position1.ModuleID",
    #     ]
    #     handles = []
    #     for node_str in nodes_to_subscribe:
    #         try:
    #             node = self.client.get_node(node_str)
    #             handle = await self.subscription.subscribe_data_change(node)
    #             handles.append(handle)
    #             self.add_log_message("opcua.subscribedToNode", "info", node_id=node_str)
    #         except Exception as e:
    #             self.add_log_message("opcua.subscribeError", "error", node_id=node_str, error=str(e))
    #             print(f"Error subscribing to node {node_str}: {e}")
    #     if not handles:
    #         self.add_log_message("opcua.noSubscriptions", "warning")

# За да използвате OpcUaManager, ще трябва да го инстанцирате и да извикате неговите async методи
# в рамките на asyncio event loop, обикновено в отделна нишка или с помощта на `asyncio.run()`.
# Например, в app.py:
# opc_manager = OpcUaManager(Config.OPCUA_SERVER_URL, Config.OPCUA_NAMESPACE, socketio, global_line_status_data, translation_data)
# def opcua_thread_target():
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         loop.run_until_complete(opc_manager.connect())
#         if opc_manager.running:
#             loop.run_forever() # Or some other way to keep it running and processing subscriptions
#     except KeyboardInterrupt:
#         pass
#     finally:
#         if opc_manager.running:
#             loop.run_until_complete(opc_manager.disconnect())
#         loop.close()
# opcua_thread = threading.Thread(target=opcua_thread_target, daemon=True)
# opcua_thread.start()