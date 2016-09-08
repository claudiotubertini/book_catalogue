# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_series import Series, Base, Volume

engine = create_engine('sqlite:///bookcatalogue.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

series = [{'name': 'Studi e Ricerche', 'id': '1', 
'description': 'ANMLI è la più antica associazione museale italiana, fondata nel 1950 per promuovere la tutela dei musei e del patrimonio cultuale di proprietà e pertinenza degli enti locali e istituzionali.', 
'director': 'ANMLI'}, 
{'name':'CentoPagine', 'id':'2', 'description': 'Collana di saggi brevi dedicatia temi e problemi classici, utile lettura di approfondimento per tutti gli studiosi', 'director': 'Stefano Calabrese, Alberto De Bernardi, Elisabetta Menetti, Guglielmo Pescatore'},
{'name':'Scena arborata', 'id':'3', 'description': 'Teatro italiano dei secoli XVI e XVII: testi e studi.', 'director': 'Riccardo Drusi, Daria Perocco, Elisabetta Selmi, Piermario Vescovo'}]


volume = [ {'title':'Contrastiva. Grammatica della lingua spagnola', 
'description':'Contrastiva è il risultato di una ricerca sulla descrizione e sulla didattica della lingua spagnola per italofoni realizzata da esperti nel settore.', 
'price':'euro 32.00','id':'1', 'series_id':'1', 'author': 'Juan Carlos Barbero, Felisa Bermejo, Félix San Vicente'},
 {'title':'Storia del Cinema Sperimentale',
 'description':'In questo testo l\'autore propone la sua interpretazione del contributo che il cinema sperimentale ha fornito all\'affermarsi del cinema come arte autonoma, dotata di un suo statuto specifico', 
 'price':'euro 24.00', 'id':'2', 'series_id':'2', 'author':'Claudio Tubertini'},
{'title':'Giovani e generazioni in Italia. Lo stato della ricerca', 
'description':'Made with fresh organic vegetables','price':'euro 25.00', 'id':'3', 'series_id':'3', 'author':'Fabiana Bicciré'}]


# l = 0
# for i in series:
	
# 	session.add(Series(name=i['name'], description=i['description'], director=i['director'], id=i['id']))
# 	session.commit()
 # title = Column(String(80), nullable=False)
 #    id = Column(Integer, primary_key=True)
 #    description = Column(String(250))
 #    price = Column(String(8))
 #    author = Column(String(250))
 #    series_id = Column(Integer, ForeignKey('series.id'))

for j in volume:
	session.add(Volume(title=j['title'], description=j['description'], price=j['price'], author=j['author'], series_id=j['series_id']))
	session.commit()

