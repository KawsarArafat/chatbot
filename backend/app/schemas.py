from pydantic import BaseModel,Field
class ConversationCreate(BaseModel):
    title:str='New chat'
    document_ids:list[str]=Field(default_factory=list)
class ConversationPatch(BaseModel):
    title:str|None=None
    document_ids:list[str]|None=None
class MessageCreate(BaseModel):
    content:str=Field(min_length=1,max_length=12000)
