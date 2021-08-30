
class sharedData:
    def __init__(self, data:dict):
        if data.get('data'):
            post_data = data['data']['shortcode_media']
        elif data.get('entry_data'):
            post_data = data['entry_data']['PostPage'][0]['graphql']['shortcode_media']
            self.shortcode = post_data['shortcode']
            self.post_context = post_data['edge_media_to_caption']['edges'][0]['node']['text']
        elif data.get('graphql'):
            post_data = data['graphql']['shortcode_media']
        
        self.has_next_page = post_data['edge_media_to_parent_comment']['page_info']['has_next_page']
        self.end_cursor = post_data['edge_media_to_parent_comment']['page_info']['end_cursor']
        self.comments = post_data['edge_media_to_parent_comment']['edges']
        self.comments_count = post_data['edge_media_to_parent_comment']['count']
        
class commentNode:
    def __init__(self, comment_node:dict):
        self.author = comment_node['owner']['username']
        self.thumbnail = comment_node['owner']['profile_pic_url']
        self.context = comment_node['text']
        self.timestamp = comment_node['created_at']
        self.likes = comment_node['edge_liked_by']['count']
        
        if comment_node.get('edge_threaded_comments'):
            self.sub_comments = comment_node['edge_threaded_comments']['edges']