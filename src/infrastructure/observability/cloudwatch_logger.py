from __future__ import annotations

import json
import time
from typing import List, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from src.infrastructure.config.settings import settings


class CloudWatchLogger:
    def __init__(self,
                 region_name: Optional[str] = None,
                 log_group: Optional[str] = None):
        self.client = boto3.client('logs', region_name=region_name or settings.mobile_logs_region)
        self.log_group = log_group or settings.mobile_logs_group
        self._sequence_tokens: Dict[str, str] = {}
        self._ensure_log_group()

    def _ensure_log_group(self) -> None:
        try:
            self.client.create_log_group(logGroupName=self.log_group)
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass

    def _ensure_stream(self, stream_name: str) -> None:
        try:
            self.client.create_log_stream(logGroupName=self.log_group, logStreamName=stream_name)
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass

    def _describe_stream(self, stream_name: str) -> Optional[str]:
        resp = self.client.describe_log_streams(
            logGroupName=self.log_group,
            logStreamNamePrefix=stream_name,
            limit=1,
        )
        streams = resp.get('logStreams', [])
        if streams and streams[0]['logStreamName'] == stream_name:
            return streams[0].get('uploadSequenceToken')
        return None

    def put_events(self, user_hash: str, events: List[Dict]) -> None:
        stream = f"user/{user_hash or 'unknown'}"
        self._ensure_stream(stream)
        token = self._sequence_tokens.get(stream) or self._describe_stream(stream)
        input_events = []
        for e in events:
            # ts_iso to epoch ms if present
            ts = int(time.time() * 1000)
            if 'ts_iso' in e:
                try:
                    ts = int(time.mktime(time.strptime(e['ts_iso'].split('.')[0], "%Y-%m-%dT%H:%M:%S")) * 1000)
                except Exception:
                    pass
            input_events.append({
                'timestamp': ts,
                'message': json.dumps(e, ensure_ascii=False),
            })

        kwargs = dict(logGroupName=self.log_group, logStreamName=stream, logEvents=input_events)
        if token:
            kwargs['sequenceToken'] = token
        try:
            resp = self.client.put_log_events(**kwargs)
            next_token = resp.get('nextSequenceToken')
            if next_token:
                self._sequence_tokens[stream] = next_token
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'InvalidSequenceTokenException':
                # refresh token and retry once
                token = self._describe_stream(stream)
                kwargs['sequenceToken'] = token
                resp = self.client.put_log_events(**kwargs)
                next_token = resp.get('nextSequenceToken')
                if next_token:
                    self._sequence_tokens[stream] = next_token
            else:
                raise


