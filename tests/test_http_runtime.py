"""Real local HTTP tests: no requests reach Discord or OpenRouter."""
import asyncio
import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiohttp import web

import bot as application
import utils.clash as clash


@pytest_asyncio.fixture
async def client_bot(monkeypatch):
    bot = application.PippoBot()
    bot.production = False
    pool = NS(close=AsyncMock())
    monkeypatch.setattr(application.asyncpg, 'create_pool', AsyncMock(return_value=pool))
    monkeypatch.setattr(bot.tree, 'sync', AsyncMock())
    await bot._async_setup_hook()
    await bot.setup_hook()
    session = bot.http_session
    try:
        yield bot
    finally:
        await bot.close()
        assert session.closed
        pool.close.assert_awaited_once()


@pytest_asyncio.fixture
async def api(monkeypatch):
    state = NS(active=0, peak=0, requests=[], mode='valid')
    async def handler(request):
        state.active += 1
        state.peak = max(state.active,state.peak)
        try:
            payload = await request.json()
            assert request.headers['Authorization']=='Bearer local-test-key'
            assert payload['response_format']['json_schema']['strict'] is True
            assert payload['provider']['require_parameters'] is True
            assert payload['provider']['zdr'] is True
            assert payload['max_tokens']==2048
            state.requests.append(payload)
            await asyncio.sleep(.01)
            if state.mode == 'rate_limit':
                return web.json_response({'error': {'message':'busy'}},status=429)
            if state.mode == 'oversize':
                return web.Response(body=b' '*(256*1024+1),content_type='application/json')
            creation=json.loads(payload['messages'][1]['content'])['player1']['creation']
            result={'winner':1,'reason':creation}
            if state.mode=='list': result=[]
            if state.mode=='null': result=None
            if state.mode=='invalid_winner': result={'winner':True,'reason':creation}
            if state.mode=='missing_reason': result={'winner':1}
            body=json.dumps({'choices':[{'message':{'content':json.dumps(result)}}]}).encode()
            if state.mode=='chunked':
                response=web.StreamResponse(headers={'Content-Type':'application/json'})
                await response.prepare(request)
                for offset in range(0,len(body),7):
                    await response.write(body[offset:offset+7])
                    await asyncio.sleep(0)
                await response.write_eof()
                return response
            return web.Response(body=body,content_type='application/json')
        finally:
            state.active -= 1
    app=web.Application()
    app.router.add_post('/api/v1/chat/completions',handler)
    runner=web.AppRunner(app)
    await runner.setup()
    site=web.TCPSite(runner,'127.0.0.1',0)
    await site.start()
    port=site._server.sockets[0].getsockname()[1]
    monkeypatch.setattr(clash,'CHAT_COMPLETIONS_URL',f'http://127.0.0.1:{port}/api/v1/chat/completions')
    monkeypatch.setenv('OPENROUTER_API_KEY','local-test-key')
    monkeypatch.delenv('OPENROUTER_MODEL',raising=False)
    try:
        yield state
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_eighty_actual_http_judgments_share_bounded_pool(client_bot,api):
    players=[NS(display_name=f'Player {n}') for n in range(80)]
    opponent=NS(display_name='Pippo')
    results=await asyncio.gather(*(clash.judge_clash(p,f'Creation {n}',opponent,'Bot',bot=client_bot) for n,p in enumerate(players)))
    assert len(api.requests)==80
    assert 1 < api.peak <= 8
    for n,(winner,reason) in enumerate(results):
        assert winner is players[n]
        assert reason==f'Creation {n}'
    assert api.requests[0]['reasoning']=={'effort':'low','exclude':True}
    assert not client_bot.http_session.closed


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['list','null','invalid_winner','missing_reason','rate_limit','oversize'])
async def test_bad_provider_results_fall_back_without_breaking_next_game(client_bot,api,mode):
    api.mode=mode
    first,second=NS(display_name='First'),NS(display_name='Second')
    winner,reason=await clash.judge_clash(first,'First creation',second,'Second creation',bot=client_bot)
    assert winner in (first,second)
    assert reason.startswith('[Random fallback')
    api.mode='valid'
    winner,reason=await clash.judge_clash(first,'Next valid creation',second,'Second creation',bot=client_bot)
    assert winner is first and reason=='Next valid creation'


@pytest.mark.asyncio
async def test_chunked_judgment_reads_through_eof(client_bot,api):
    api.mode='chunked'
    first,second=NS(display_name='First'),NS(display_name='Second')
    assert await clash.judge_clash(first,'Chunked result',second,'Other',bot=client_bot)==(first,'Chunked result')
