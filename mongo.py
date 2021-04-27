from mongoengine import *
from datetime import datetime

h = open('property.txt').read().splitlines()
connect(db='kol_db', host=h[2])

class Kol(Document):
    user_id = IntField(default=0, required=True, primary_key=True)
    name = StringField(max_length=50,null=True)
    avatar = StringField(null=True)
    description = StringField(null=True)
    categories = ListField(null=True)
    tags = ListField(null=True)
    gender = StringField(max_length=5,null=True)
    created_at = DateTimeField(default=datetime.now(), required=True)
    updated_at = DateTimeField(default=datetime.now(), required=True)
    yt_sub = ListField(null=True)
    ig_sub = ListField(null=True)
    fb_sub = ListField(null=True)

class IgRecord(Document):
    user_id = IntField(null=True)
    name = StringField(null=True)
    follow_count = StringField(null=True)
    instagram_url = StringField(null=True)
    created_at = DateField(null=True)
    records = ListField(null=True)

def get_ig_id_url():
    '''return ig url list'''
    _output = []
    for ig in IgRecord.objects:
        _output.append((ig.user_id, ig.instagram_url))
    # print(_output)
    return _output[:10]

def update_ig_s_count(id,count):
    # Update Kol
    update_list = deepcopy(Kol.objects(user_id=id)[0].ig_sub)
    update_list[0]['subscribe'] = count
    Kol.objects(user_id=id).update(set__ig_sub=update_list)
    
    # Update Ig_record
    IgRecord.objects(user_id=id).update(set__follow_count=count)
