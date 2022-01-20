
from requests.api import post


class sharedData:
    def __init__(self, data:dict):
        if data.get('data'):
            try:
                post_data = data['data']['shortcode_media']
            except KeyError:
                post_data = data['data']['comment']
        elif data.get('entry_data'):
            post_data = data['entry_data']['PostPage'][0]['graphql']['shortcode_media']
            self.shortcode = post_data['shortcode']
            self.post_context = post_data['edge_media_to_caption']['edges'][0]['node']['text']
        elif data.get('graphql'):
            post_data = data['graphql']['shortcode_media']
        
        try:
            post_data = post_data['edge_media_to_parent_comment']
        except KeyError:
            post_data = post_data['edge_threaded_comments']
        
        self.has_next_page = post_data['page_info']['has_next_page']
        self.end_cursor = post_data['page_info']['end_cursor']
        self.comments = post_data['edges']
        self.comments_count = post_data['count']
        
class commentNode:
    def __init__(self, comment_node:dict):
        self.comment_id = comment_node['id']
        self.author = comment_node['owner']['username']
        self.thumbnail = comment_node['owner']['profile_pic_url']
        self.context = comment_node['text']
        self.timestamp = comment_node['created_at']
        self.likes = comment_node['edge_liked_by']['count']
        
        if comment_node.get('edge_threaded_comments'):
            self.sub_comments = comment_node['edge_threaded_comments']['edges']
            self.sub_end_cursor = comment_node['edge_threaded_comments']['page_info']['end_cursor']
        else:
            self.sub_comments = []

class CommentItem:
    def __init__(self, comment_node) -> None:
        self.comment_id = comment_node['pk']
        self.author = comment_node['user']['username']
        self.thumbnail = comment_node['user']['profile_pic_url']
        self.context = comment_node.get('text')
        self.published_time = comment_node.get('created_at')
        self.likes = comment_node.get('comment_like_count')
        self.replies = []

class PostLoginItem:
    def __init__(self, json_data:dict) -> None:
        data = json_data['items'][0]
        self.like = data.get('like_count')
        self.comment = data.get('comment_count')
        
class PostAsyncItem:
    def __init__(self, json_data) -> None:
        data = json_data['graphql']['shortcode_media']
        self.like = data['edge_media_preview_like']['count']
        self.comment = data['edge_media_preview_comment']['count']

class ProfileLoginItem:
    def __init__(self, json_data) -> None:
        self.followers = json_data['graphql']['user']['edge_followed_by']['count']