"""Tiny Buffer GraphQL client (https://developers.buffer.com)."""
import json, os, time, urllib.request, urllib.error

API = "https://api.buffer.com"


def gql(query, variables=None, retries=3):
    key = os.environ.get("BUFFER_API_KEY")
    if not key:
        raise SystemExit("BUFFER_API_KEY is not set")
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    for attempt in range(retries):
        req = urllib.request.Request(API, data=body, method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(60); continue
            raise RuntimeError(f"Buffer {e.code}: {e.read().decode(errors='ignore')[:500]}")
        if out.get("errors"):
            raise RuntimeError(f"Buffer GraphQL error: {json.dumps(out['errors'])[:800]}")
        return out["data"]


def organization_id():
    d = gql("query { account { organizations { id name } } }")
    return d["account"]["organizations"][0]["id"]


def channels(org_id):
    d = gql("query($o: OrganizationId!){ channels(input:{organizationId:$o}){ id name service isDisconnected } }",
            {"o": org_id})
    return d["channels"]


def create_video_post(channel_id, service, caption, video_url, youtube_title, draft=True):
    meta = {}
    if service == "instagram":
        meta = {"instagram": {"type": "reel", "shouldShareToFeed": True}}
    elif service == "youtube":
        meta = {"youtube": {"title": youtube_title[:95], "categoryId": "28"}}
    q = """mutation($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id status dueAt } }
        ... on MutationError { message }
      } }"""
    inp = {"text": caption, "channelId": channel_id, "schedulingType": "automatic", "mode": "addToQueue",
           "assets": [{"video": {"url": video_url, "metadata": {"thumbnailOffset": 1500}}}],
           "metadata": meta, "saveToDraft": bool(draft)}
    r = gql(q, {"input": inp})["createPost"]
    if "post" not in r:
        raise RuntimeError(f"createPost failed for {service}: {r.get('message')}")
    return r["post"]


def post_metrics(post_id):
    d = gql("query($i: PostId!){ post(input:{id:$i}){ id status dueAt metrics{ type value unit } } }", {"i": post_id})
    return d["post"]
