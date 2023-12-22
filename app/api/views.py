import logging, os, json, redis
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from worker.tasks import run_bot_exe

logger = logging.getLogger(__name__)
redis_client = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            decode_responses=True)


@api_view(['GET'])
def check_bot(request, format=None):
    key = os.environ.get('SUB_API_KEY')

    if request.META['HTTP_AUTHORIZATION'] is None or key != request.META['HTTP_AUTHORIZATION']:
        return Response('', status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        data = request.data
        return Response(data, status=status.HTTP_201_CREATED)

    return Response('', status=status.HTTP_403_FORBIDDEN)


@api_view(['POST'])
def run_bot(request, format=None):
    key = os.environ.get('SUB_API_KEY')

    if request.META['HTTP_AUTHORIZATION'] is None or key != request.META['HTTP_AUTHORIZATION']:
        return Response('', status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'POST':
        data = request.data
        if 'nonce' in data:
            run_bot_exe.delay(data['nonce'])
        
        return Response(data, status=status.HTTP_201_CREATED)

    return Response('', status=status.HTTP_403_FORBIDDEN)
