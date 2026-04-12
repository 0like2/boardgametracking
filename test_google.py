from googlesearch import search
query = 'site:boardgamegeek.com/boardgame "The Crew: The Quest for Planet Nine"'
for j in search(query, num_results=1):
    print(j)
