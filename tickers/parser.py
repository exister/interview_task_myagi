import typing
import asyncio
import logging
from aiohttp import ClientSession, ClientTimeout, ClientResponseError
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Parser:
    BASE_URL = "https://finance.yahoo.com/quote/"
    SESSION = ClientSession(timeout=ClientTimeout(connect=30, sock_read=120))
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/74.0.3729.169 YaBrowser/19.6.0.1583 Yowser/2.5 Safari/537.36"
    )

    def __init__(self, ticker: str):
        """

        Args:
            ticker:
        """
        self.ticker = ticker

    @classmethod
    async def load(
        cls, tickers: typing.Union[typing.List[str], typing.Tuple[str], str]
    ) -> typing.Optional[typing.List[typing.Dict[str, typing.Any]]]:
        if not isinstance(tickers, (tuple, list)):
            tickers = [tickers]

        try:
            return await asyncio.gather(*[cls._load(t) for t in tickers])
        except Exception as e:
            logger.exception(e)

    @classmethod
    async def _load(cls, ticker) -> typing.Optional[typing.Dict[str, typing.Any]]:
        try:
            resource = await cls.load_resource(ticker)
            res = await cls.process_html(resource)
            res["ticker"] = ticker
            return res
        except Exception as e:
            logger.exception(e)

    @classmethod
    async def load_resource(cls, ticker) -> str:
        res = await cls.SESSION.get(
            f"{cls.BASE_URL}{ticker}",
            headers={
                "User-Agent": cls.USER_AGENT,
                "Accept": "text/html",
                "Accept-Language": "en,ru;q=0.9,cs;q=0.8,la;q=0.7",
                "Accept-Encoding": "gzip, deflate",
            },
        )
        if res.status != 200 or "lookup" in res.url.path:
            raise ClientResponseError(
                res.request_info, res.history, status=res.status, message=res.reason, headers=res.headers
            )
        return await res.text(encoding="utf-8")

    @classmethod
    async def process_html(cls, html: str) -> dict:
        return await asyncio.get_event_loop().run_in_executor(None, cls._process_html, html)

    @classmethod
    def _process_html(cls, html: str) -> dict:
        soup = BeautifulSoup(markup=html, features="html5lib", from_encoding="utf-8")
        result = {}
        cls._parse_last_price(soup, result)
        cls._parse_summary(soup, result)
        return result

    @classmethod
    def _parse_last_price(cls, soup: BeautifulSoup, result: dict):
        last_price, price_change = soup.select("#quote-header-info > div")[-1].find_all("span")[:2]
        price_change = list(map(float, price_change.text.replace("(", "").replace(")", "").replace("%", "").split(" ")))

        result["last_price"] = {
            "price": float(last_price.text),
            "change_absolute": price_change[0],
            "change_percent": price_change[1],
        }

    @classmethod
    def _parse_summary(cls, soup: BeautifulSoup, result: dict):
        summary = {}
        for tr in soup.select("#quote-summary tr"):
            if len(tr.contents) == 2:
                summary[tr.contents[0].text] = tr.contents[1].text

        result["last_summary"] = summary


if __name__ == "__main__":
    res = asyncio.get_event_loop().run_until_complete(Parser.load(["AAPL", "TSLA", "ffff"]))
    print(res)
    asyncio.get_event_loop().run_until_complete(Parser.SESSION.close())
