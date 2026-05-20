from ib_insync import IB, Future


class IBKRClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 4001, client_id: int = 1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id

    def connect(self):
        self.ib.connect(self.host, self.port, clientId=self.client_id)

    def disconnect(self):
        self.ib.disconnect()

    def get_contract_details(self, symbol: str, exchange: str, currency: str = "USD"):
        contract = Future(symbol=symbol, exchange=exchange, currency=currency)
        return self.ib.reqContractDetails(contract)

    def get_historical_bars(self, contract, duration: str = "2 Y", bar_size: str = "1 day"):
        return self.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=True,
        )

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()
