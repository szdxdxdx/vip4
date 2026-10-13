"""任务聊天回归，使用假 RPC 与本地协议子进程，不调用 LLM。"""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi import FastAPI
from app.agent.pi import PiAgent
from app.service.api import router
from app.vip_task.task import Task, TaskConflictError, TaskMetadataError
from app.vip_task.task_manager import TaskManager
from app.vip_task.task import TaskPathError

class MockPi:
    instances = []
    active = peak = 0
    def __init__(self):
        self.events = asyncio.Queue()
        self.settled = self.closed = False
        self.commands, self.inputs = [], []
        self.worker = None
        MockPi.instances.append(self)
        MockPi.active += 1
        MockPi.peak = max(MockPi.active, MockPi.peak)
    async def start_reader(self):
        pass
    async def rpc(self, command, **fields):
        self.commands.append((command, fields))
        if command == 'prompt':
            self.inputs.append(fields['message'])
            if self.worker is None:
                self.worker = asyncio.create_task(self.work())
            return {'disposition': 'queued' if 'streamingBehavior' in fields else 'started'}
        return {}
    async def work(self):
        while self.inputs:
            content = self.inputs.pop(0)
            await self.events.put({'type': 'message_start', 'message': {'role': 'user', 'content': [{'type': 'text', 'text': content}]}})
            await asyncio.sleep(.04)
            await self.events.put({'type': 'message_end', 'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': content}], 'stopReason': 'stop'}})
        self.settled = True
        await self.events.put({'type': 'agent_settled', 'aborted': False})
    async def abort(self):
        self.commands.append(('clear_queue', {}))
        self.inputs.clear()
        if self.worker:
            self.worker.cancel()
            await asyncio.gather(self.worker, return_exceptions=True)
        await asyncio.sleep(.01)
        self.commands.append(('abort', {}))
        self.settled = True
        await self.events.put({'type': 'agent_settled', 'aborted': True})
    async def stop_reader(self):
        self.closed = True
        MockPi.active -= 1

class ChatTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.config = patch('app.vip_task.config.VIP_TASK_DIR', self.root)
        self.config.start()
        MockPi.instances = []
        MockPi.active = MockPi.peak = 0
        self.original_create_agent = Task._create_agent
        self.agent = patch.object(Task, '_create_agent', lambda task: MockPi())
        self.agent.start()
        self.manager = TaskManager()
    async def asyncTearDown(self):
        await self.manager.close()
        self.agent.stop()
        self.config.stop()
        self.directory.cleanup()
    async def ready(self, name='chat'):
        self.manager.create_task(name, '初始输入', start=False)
        task = self.manager.tasks[name]
        task.set_status('failed')
        return task
    async def wait_agent(self, task):
        async with asyncio.timeout(2):
            while task.agent is None or not task.agent.commands:
                await asyncio.sleep(.001)
        return task.agent
    async def test_multiturn_replay_idle(self):
        task = await self.ready()
        for text in ['第一轮', '第二轮']:
            await self.manager.send_message('chat', text)
            await task.job
        lines = [json.loads(line) async for line in self.manager.get_events('chat')]
        self.assertEqual([e['message'] for e in lines if e['type'] == 'user'], ['第一轮', '第二轮'])
        self.assertEqual([e['event_id'] for e in lines], list(range(1, len(lines)+1)))
        self.assertEqual(self.manager.get_task('chat')['task']['chatstatus'], 'idle')
        self.assertEqual(len(MockPi.instances), 2)
        restored = Task('chat')
        self.assertEqual(restored.events, task.events)
        self.assertEqual(restored.turn_id, 2)
    async def test_followup_order_single_process(self):
        task = await self.ready()
        await self.manager.send_message('chat', '一')
        agent = await self.wait_agent(task)
        await self.manager.send_message('chat', '二')
        await self.manager.send_message('chat', '三')
        await task.job
        prompts = [f for c, f in agent.commands if c == 'prompt']
        self.assertEqual([p['message'] for p in prompts], ['一', '二', '三'])
        self.assertTrue(all(p['streamingBehavior'] == 'followUp' for p in prompts[1:]))
        self.assertEqual(len(MockPi.instances), 1)
        users = [json.loads(line)['message'] for line in task.events if json.loads(line)['type'] == 'user']
        self.assertEqual(users, ['一', '二', '三'])
    async def test_pause_release_resume_pending(self):
        task = await self.ready()
        await self.manager.send_message('chat', '开始')
        agent = await self.wait_agent(task)
        await self.manager.send_message('chat', '待消费补充')
        result = await self.manager.pause_task('chat')
        self.assertEqual(result['status'], 'paused')
        self.assertTrue(agent.closed)
        self.assertEqual(MockPi.active, 0)
        self.assertEqual([c for c, _ in agent.commands][-2:], ['clear_queue', 'abort'])
        self.assertEqual(task.pending, ['待消费补充'])
        await self.manager.send_message('chat', '继续')
        await task.job
        self.assertIn('待消费补充', MockPi.instances[-1].commands[0][1]['message'])
        self.assertEqual(MockPi.peak, 1)
    async def test_queued_pause_project_waiter(self):
        blocker = await self.ready('blocker')
        await self.manager.send_message('blocker', '占用')
        await self.wait_agent(blocker)
        self.manager.create_task('project', '验证', start=False)
        waiter = asyncio.create_task(self.manager.run_task('project'))
        await asyncio.sleep(.005)
        await self.manager.pause_task('project')
        await asyncio.wait_for(waiter, 1)
        self.assertEqual(self.manager.get_task('project')['task']['status'], 'paused')
        self.assertEqual(len(MockPi.instances), 1)
        await self.manager.pause_task('blocker')
        self.assertFalse(self.manager.execution_lock.locked())
    async def test_created_and_metadata_types(self):
        self.manager.create_task('new', '输入', start=False)
        with self.assertRaises(TaskConflictError):
            await self.manager.send_message('new', '不能冲掉准备')
        task = self.manager.tasks['new']
        self.assertEqual(Task._metadata(task.task_dir)['turn_id'], 0)
        path = task.task_dir / 'task.json'
        original = json.loads(path.read_text())
        for change in ({'turn_id': 2}, {'chatstatus': 'idle'}):
            path.write_text(json.dumps({**original, **change}))
            Task._metadata(task.task_dir)
        for change in ({'turn_id': '2'}, {'turn_id': True}, {'turn_id': -1}, {'status': None}):
            path.write_text(json.dumps({**original, **change}))
            with self.assertRaises(TaskMetadataError):
                Task._metadata(task.task_dir)
        path.write_text(json.dumps({'turn_id': 2}))
        with self.assertRaises(TaskMetadataError):
            Task._metadata(task.task_dir)
        path.write_text(json.dumps(original))
    async def test_old_report_not_success(self):
        task = await self.ready()
        output = task.task_dir / 'workspace' / 'cbmc_suite' / 'output'
        output.mkdir(parents=True)
        (output / 'report.json').write_text('{}')
        (output / 'report.html').write_text('旧报告')
        task.chat_mode = False
        await task.run()
        self.assertEqual(Task._metadata(task.task_dir)['status'], 'failed')
        self.assertEqual(Task._metadata(task.task_dir)['reports'], [])
    async def test_pause_delete_shutdown_race(self):
        task = await self.ready()
        await self.manager.send_message('chat', '启动')
        agent = await self.wait_agent(task)
        pause = asyncio.create_task(self.manager.pause_task('chat'))
        await asyncio.sleep(0)
        delete = asyncio.create_task(self.manager.delete_task('chat'))
        await asyncio.gather(pause, delete)
        self.assertTrue(agent.closed)
        self.assertFalse(task.task_dir.exists())
        other = await self.ready('other')
        await self.manager.send_message('other', '启动')
        await self.wait_agent(other)
        await self.manager.close()
        self.assertEqual(MockPi.active, 0)
        self.assertEqual(Task._metadata(other.task_dir)['status'], 'cancelled')
    async def test_paused_continue_report_and_plain_chat_preserves_verification(self):
        task = await self.ready()
        task.chat_mode = True
        task.set_status('paused')
        async def report_events(task, prompt):
            output = task.task_dir / 'workspace' / 'cbmc_suite' / 'output'
            output.mkdir(parents=True, exist_ok=True)
            (output / 'report.json').write_text('{}')
            (output / 'report.html').write_text('新报告')
            yield {'type': 'agent_settled', 'aborted': False}
        with patch.object(Task, '_agent_events', report_events):
            await self.manager.send_message('chat', '继续验证')
            await task.job
        metadata = Task._metadata(task.task_dir)
        self.assertEqual(metadata['status'], 'completed')
        self.assertEqual(metadata['verification_status'], 'completed')
        reports = metadata['reports']
        await self.manager.send_message('chat', '解释报告')
        await task.job
        metadata = Task._metadata(task.task_dir)
        self.assertEqual(metadata['status'], 'idle')
        self.assertEqual(metadata['verification_status'], 'completed')
        self.assertEqual(metadata['reports'], reports)

    async def test_rpc_failure_not_validated_by_old_report(self):
        task = await self.ready()
        async def broken(task, prompt):
            yield {'type': 'error', 'error': '模型失败'}
        output = task.task_dir / 'workspace' / 'cbmc_suite' / 'output'
        output.mkdir(parents=True)
        (output / 'report.json').write_text('{}')
        (output / 'report.html').write_text('旧报告')
        with patch.object(Task, '_agent_events', broken):
            await task.run()
        metadata = Task._metadata(task.task_dir)
        self.assertEqual(metadata['status'], 'failed')
        self.assertEqual(metadata['verification_status'], 'failed')
        self.assertEqual(metadata['reports'], [])

    async def test_session_arguments_are_task_specific(self):
        task = await self.ready()
        directory = task.task_dir / 'pi_session'
        history = directory / 'old.jsonl'
        history.write_text('{}')
        with patch('app.vip_task.task.PiAgent') as factory, patch('app.vip_task.config.VIP_SKILL_DIR', self.root):
            self.original_create_agent(task)
            argv = factory.call_args.kwargs['argv']
            self.assertEqual(argv[argv.index('--session') + 1], str(history))
            self.assertNotIn('--resume', argv)
            self.assertNotIn('--continue', argv)
            self.assertNotIn('必须且只能是', ' '.join(argv))
            self.original_create_agent(task)
            self.assertEqual(factory.call_args.kwargs['argv'], argv)

    async def test_legacy_completed_task_preserves_verification_when_chatting(self):
        task = await self.ready()
        task.set_status('completed')
        session = task.task_dir / 'pi_session' / 'conversation.jsonl'
        records = [
            {'type': 'session', 'version': 3, 'id': 'existing-session'},
            {'type': 'message', 'id': 'user-one', 'parentId': None,
             'message': {'role': 'user', 'content': [{'type': 'text', 'text': '原始输入'}]}},
        ]
        session.write_text(''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records))
        await self.manager.send_message('chat', '解释报告')
        await task.job
        metadata = Task._metadata(task.task_dir)
        self.assertEqual(metadata['status'], 'idle')
        self.assertEqual(metadata['verification_status'], 'completed')

    async def test_header_only_session_replays_original_input_after_restart(self):
        self.manager.create_task('header-only', '原始验证输入', start=False)
        task = self.manager.tasks['header-only']
        task.write_event({'type': 'user', 'message': '原始验证输入'})
        task.set_status('paused')
        (task.task_dir / 'pi_session' / 'conversation.jsonl').write_text(
            json.dumps({'type': 'session', 'version': 3, 'id': 'empty-session',
                        'timestamp': '2026-10-13T00:00:00Z', 'cwd': str(task.task_dir / 'workspace')}) + '\n')
        self.manager.tasks.pop('header-only')
        await self.manager.send_message('header-only', '继续')
        await self.manager.tasks['header-only'].job
        prompts = [fields['message'] for agent in MockPi.instances
                   for command, fields in agent.commands if command == 'prompt']
        self.assertIn('原始验证输入', prompts[0])
        self.assertEqual(prompts[-1], '继续')

    async def test_journal_symlink_cannot_read_or_append_outside_task(self):
        task = await self.ready()
        outside = self.root / 'outside.jsonl'
        content = json.dumps({'type': 'user', 'message': '任务外信息', 'turn_id': 1}) + '\n'
        outside.write_text(content)
        journal = task.task_dir / 'chat_events.jsonl'
        journal.symlink_to(outside)
        with self.assertRaises(TaskPathError):
            Task('chat')
        with self.assertRaises(TaskPathError):
            task.write_event({'type': 'user', 'message': '不可越界'})
        self.assertEqual(outside.read_text(), content)
        self.assertEqual(task.events, [])
        journal.unlink()

    async def test_session_symlinks_cannot_open_another_context(self):
        task = await self.ready()
        outside = self.root / 'outside-session.jsonl'
        outside.write_text('其他会话')
        directory = task.task_dir / 'pi_session'
        fixed = directory / 'conversation.jsonl'
        fixed.symlink_to(outside)
        with self.assertRaises(TaskPathError):
            task.session_path()
        fixed.unlink()
        directory.rmdir()
        external_directory = self.root / 'external-session'
        external_directory.mkdir()
        directory.symlink_to(external_directory, target_is_directory=True)
        try:
            with self.assertRaises(TaskPathError):
                task.session_path()
            with patch('app.vip_task.task.PiAgent') as process, patch('app.vip_task.config.VIP_SKILL_DIR', self.root):
                with self.assertRaises(TaskPathError):
                    self.original_create_agent(task)
                process.assert_not_called()
        finally:
            directory.unlink()
            directory.mkdir()
        self.assertEqual(outside.read_text(), '其他会话')

    async def test_cold_task_with_corrupt_journal_can_be_permanently_deleted(self):
        task = await self.ready()
        (task.task_dir / 'chat_events.jsonl').write_text('{损坏的对话记录')
        self.manager.tasks.pop('chat')
        self.assertEqual((await self.manager.delete_task('chat'))['status'], 'deleted')
        self.assertFalse(task.task_dir.exists())

    async def test_journal_fifo_is_rejected_without_blocking(self):
        import os
        task = await self.ready()
        journal = task.task_dir / 'chat_events.jsonl'
        os.mkfifo(journal)
        with self.assertRaises(TaskPathError):
            Task('chat')
        with self.assertRaises(TaskPathError):
            task.write_event({'type': 'user', 'message': '不可写入特殊文件'})
        journal.unlink()

    async def test_late_settled_does_not_close_new_prompt(self):
        class RacingPi(MockPi):
            checks = 0
            async def rpc(self, command, **fields):
                self.commands.append((command, fields))
                if command == 'get_state':
                    self.checks += 1
                    return {'isStreaming': self.checks == 1}
                if command == 'prompt':
                    if 'streamingBehavior' in fields:
                        await self.events.put({'type': 'agent_settled', 'aborted': False})
                    await self.events.put({'type': 'message_start', 'message': {'role': 'user', 'content': fields['message']}})
                    await self.events.put({'type': 'message_end', 'message': {'role': 'assistant', 'content': [], 'stopReason': 'stop'}})
                    if 'streamingBehavior' in fields:
                        await self.events.put({'type': 'agent_settled', 'aborted': False})
                    return {'disposition': 'started'}
                return {}
        task = await self.ready()
        with patch.object(Task, '_create_agent', lambda task: RacingPi()):
            await self.manager.send_message('chat', '旧轮输出')
            agent = await self.wait_agent(task)
            await self.manager.send_message('chat', '在旧结束事件到达时补充')
            await task.job
        self.assertEqual(agent.checks, 2)
        self.assertEqual(Task._metadata(task.task_dir)['status'], 'idle')
        self.assertEqual(len(MockPi.instances), 1)
        self.assertFalse(task.pending)

    async def test_multiple_tasks_share_resources_after_running_pause(self):
        first = await self.ready('first')
        second = await self.ready('second')
        await self.manager.send_message('first', '先运行')
        await self.wait_agent(first)
        await self.manager.send_message('second', '等待资源')
        await self.manager.pause_task('first')
        await second.job
        self.assertEqual(MockPi.peak, 1)
        self.assertEqual(Task._metadata(second.task_dir)['status'], 'idle')

    async def test_startup_exception_becomes_failed_event(self):
        task = await self.ready()
        with patch.object(Task, '_create_agent', side_effect=OSError('无法启动')):
            await self.manager.send_message('chat', '启动失败')
            await task.job
        self.assertEqual(Task._metadata(task.task_dir)['status'], 'failed')
        self.assertTrue(any(json.loads(line)['type'] == 'status' for line in task.events))
        self.assertFalse(self.manager.execution_lock.locked())

    async def test_identical_text_block_followups_consumed_once_each(self):
        task = await self.ready()
        await self.manager.send_message('chat', '同文')
        agent = await self.wait_agent(task)
        await self.manager.send_message('chat', '同文')
        await self.manager.send_message('chat', '同文')
        await task.job
        prompts = [f['message'] for c, f in agent.commands if c == 'prompt']
        self.assertEqual(prompts, ['同文', '同文', '同文'])
        self.assertFalse(task.pending)
        self.assertEqual(len(MockPi.instances), 1)

    async def test_skill_blocks_and_identical_initial_are_fifo(self):
        task = await self.ready()
        task.inflight = ['初始']
        task.unconfirmed_prompt = '/skill:verify-ip 继续'
        task.pending = ['/skill:verify-ip 继续', '/skill:verify-ip 继续']
        content = [{'type': 'text', 'text': '<skill name="verify-ip" location="/skills/verify-ip/SKILL.md">\n说明\n</skill>\n\n继续'}]
        task.confirm_user(content)
        self.assertEqual(len(task.pending), 2)
        self.assertFalse(task.inflight)
        task.confirm_user(content)
        self.assertEqual(len(task.pending), 1)
        task.confirm_user(content)
        self.assertFalse(task.pending)

    async def test_handled_command_not_replayed_and_rejected_input_retained(self):
        class HandledPi(MockPi):
            async def rpc(self, command, **fields):
                self.commands.append((command, fields))
                return {'disposition': 'handled'}
        task = await self.ready()
        with patch.object(Task, '_create_agent', lambda task: HandledPi()):
            await self.manager.send_message('chat', '/command')
            await task.job
        self.assertFalse(task.pending)
        self.assertEqual(Task._metadata(task.task_dir)['status'], 'idle')
        class RejectedPi(MockPi):
            async def rpc(self, command, **fields):
                if command == 'prompt':
                    raise RuntimeError('请求未接受')
                return {}
        with patch.object(Task, '_create_agent', lambda task: RejectedPi()):
            await self.manager.send_message('chat', '普通skill补充')
            await task.job
        self.assertEqual(task.pending, ['普通skill补充'])
        self.assertEqual(Task._metadata(task.task_dir)['status'], 'failed')

    async def test_api_codes(self):
        app = FastAPI()
        app.state.task_manager = self.manager
        app.include_router(router)
        await self.ready()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            r = await client.post('/task/send_message', json={'task_id': 'chat', 'message': '你好'})
            self.assertEqual(r.status_code, 202)
            r = await client.post('/task/pause_task', json={'task_id': 'chat'})
            self.assertEqual(r.json(), {'task_id': 'chat', 'status': 'paused'})
            self.assertEqual(r.status_code, 200)
            for route in ('pause_task', 'send_message'):
                self.assertEqual((await client.post('/task/'+route, json={'task_id': 'missing', 'message': 'hi'})).status_code, 404)
            self.manager.deleting.add('chat')
            self.assertEqual((await client.post('/task/pause_task', json={'task_id': 'chat'})).status_code, 409)
            self.manager.deleting.clear()
            self.assertEqual((await client.post('/task/send_message', json={'task_id': 'chat', 'message': ' '})).status_code, 400)

class RpcTests(unittest.IsolatedAsyncioTestCase):
    async def test_response_correlation_lf_and_abort(self):
        script = '''import sys,json
requests=[]
for line in sys.stdin.buffer:
 r=json.loads(line)
 if r['type']=='get_state':
  requests.append(r)
  if len(requests)==2:
   for q in reversed(requests):
    print(json.dumps({'type':'response','id':q['id'],'success':True,'data':{'marker':q['marker']}}),flush=True)
 elif r['type']=='prompt':
  print(json.dumps({'type':'message_update','delta':'a\\u2028b'}),flush=True)
  print(json.dumps({'type':'response','id':r['id'],'success':True,'data':{'disposition':'started'}}),flush=True)
 else:
  if r['type']=='abort':
   print(json.dumps({'type':'agent_settled','aborted':True}),flush=True)
  print(json.dumps({'type':'response','id':r['id'],'success':True}),flush=True)
'''
        with tempfile.TemporaryDirectory() as directory:
            agent = PiAgent(directory, argv=[sys.executable, '-u', '-c', script])
            await agent.start_reader()
            try:
                result = await asyncio.gather(agent.rpc('get_state', marker=1), agent.rpc('get_state', marker=2))
                self.assertEqual(result, [{'marker': 1}, {'marker': 2}])
                await agent.rpc('prompt', message='hi')
                self.assertEqual((await agent.events.get())['delta'], 'a\u2028b')
                await agent.abort()
                self.assertTrue(agent.settled)
            finally:
                await agent.stop_reader()
            self.assertFalse(agent.is_running())
