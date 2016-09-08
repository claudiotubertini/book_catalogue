import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()



class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))
    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'email'        : self.email,
           'picture'      : self.picture,
       }
class Volume(Base):
    __tablename__ = 'volume'

    title = Column(String(250), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    price = Column(String(8))
    author = Column(String(250))
    topic = Column(String(250))
    cover = Column(String(250))
    series_id = Column(Integer, ForeignKey('series.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    pubyear = Column(String(8))
    format_id = Column(Integer, ForeignKey('format.id'))
    formats = relationship(Format)
    

    def __repr__(self):
        return "<Volume(title='%s', description='%s', price='%s', author='%s')>" % (self.title, self.description, self.price, self.author)

    @property
    def serialize(self):
        return {
            'title'         : self.title,
            'description'   : self.description,
            'id'            : self.id,
            'price'         : self.price,
            'author'        : self.author,
            'topic'         : self.topic,
            'cover'         : self.cover,
            'series_id'     : self.series_id,
            'user'          : self.user_id,
        }
 
class Format(Base):
    __tablename__= 'format'

    id = Column(Integer, primary_key=True)
    pubformat = Column(String(80))



class Series(Base):
    __tablename__ = 'series'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, unique=True)
    description = Column(String)
    director = Column(String)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    volumes = relationship(Volume, cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<Series(name='%s' directed by '%s')>" % (self.name, self.director)

    @property
    def serialize(self):
        return {
            'name'          : self.name,
            'id'            : self.id,
            'description'   : self.description,
            'director'      : self.director,
            'user'          : self.user_id,
            'volumes'       : self.volumes,
        }


       


engine = create_engine('sqlite:///bookcatalogue2.db')


Base.metadata.create_all(engine)