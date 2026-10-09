from googlesearch import search

class extract_requirements:
    def __init__(self,query="",system = ""):
        self.query = query
        self.system = system
        self.research_result = []

    def extract_requirments(self,query,max_iterations=3):
        self.research_result = []
        answer  = search(query,num_results = max_iterations)
        self.research_result = list(answer)
        return self.research_result
        
        