import asyncio
import aiohttp
import random
from typing import List

from DatabaseManager import DatabaseManager
from Logger import Logger
from models import CouponCode
from ProxyManager import ProxyManager
from utils import USER_AGENTS


class CouponCodeScraper:
    def __init__(self):
        self.pm = ProxyManager()
        self.bearers = []
        self.db = DatabaseManager()
        self.max_attempts = 3
        self.attempt_delay = 5
        self.batch_size = 20
        self.batch_delay = 20

    async def initialize(self):
        await self.pm.initialize()
        await self.load_bearers()

    async def load_bearers(self):
        try:
            with open('auth_tokens.txt', 'r') as file:
                self.bearers = [line.strip() for line in file if line.strip()]
            Logger.info(f"Loaded {len(self.bearers)} bearer tokens")
        except FileNotFoundError:
            Logger.error("auth_tokens.txt file not found")
            raise

    async def get_coupon_code_from_token(self, bearer: str, session: aiohttp.ClientSession) -> CouponCode | None:
        for attempt in range(self.max_attempts):
            try:
                random_proxy = await self.pm.get_proxy()
                headers = {
                    'accept': '*/*',
                    'accept-language': 'en-GB,en;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6',
                    'authorization': f'Bearer {bearer}',
                    'content-type': 'application/json',
                    'dnt': '1',
                    'origin': 'https://www.studentbeans.com',
                    'priority': 'u=1, i',
                    'referer': 'https://www.studentbeans.com/',
                    'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-site',
                    'user-agent': random.choice(USER_AGENTS),
                }
                json_data = {
                    'operationName': 'createIssuanceMutation',
                    'variables': {
                        'input': {
                            'offerUid': 'aa1ccece-26ca-4b11-aca4-4f7469f3985e',
                        },
                    },
                    'query': 'mutation createIssuanceMutation($input: CreateIssuanceInput!) {\n  createIssuance(input: $input) {\n    issuance {\n      uid\n      code {\n        code\n        endDate\n        __typename\n      }\n      sbidNumber\n      affiliateLink\n      affiliateNetwork\n      __typename\n    }\n    __typename\n  }\n}',
                }

                async with session.post('https://graphql.studentbeans.com/graphql/v1/query',
                                        headers=headers,
                                        json=json_data,
                                        proxy=random_proxy.get('http') if random_proxy else None) as response:
                    response.raise_for_status()
                    data = await response.json()
                    code = str(data['data']['createIssuance']['issuance']['code']['code'])
                    coupon_code = CouponCode(code)
                    Logger.info(f"Generated coupon code: {code}")
                    return coupon_code

            except Exception as e:
                Logger.warn(f"Attempt {attempt + 1} failed for bearer {bearer}", e)
                if attempt < self.max_attempts - 1:
                    await asyncio.sleep(self.attempt_delay)
                else:
                    Logger.error(f"All attempts failed for bearer {bearer}", e)

        return None

    async def process_batch(self, batch: List[str], session: aiohttp.ClientSession) -> List[CouponCode]:
        tasks = [self.get_coupon_code_from_token(bearer, session) for bearer in batch]
        results = await asyncio.gather(*tasks)
        return [coupon for coupon in results if coupon is not None]

    async def generate_all_coupons(self):
        all_coupons = []
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(self.bearers), self.batch_size):
                batch = self.bearers[i:i + self.batch_size]
                Logger.info(
                    f"Processing batch {i // self.batch_size + 1} of {len(self.bearers) // self.batch_size + 1}")
                coupons = await self.process_batch(batch, session)
                all_coupons.extend([coupon for coupon in coupons if coupon is not None])

                if i + self.batch_size < len(self.bearers):
                    Logger.info(f"Waiting {self.batch_delay} seconds before next batch")
                    await asyncio.sleep(self.batch_delay)

        return all_coupons

    async def start(self):
        await self.initialize()
        coupons = await self.generate_all_coupons()
        Logger.info(f"Successfully fetched {len(coupons)} coupon codes out of {len(self.bearers)}")
        self.db.bulk_insert_coupon_codes(coupons)
