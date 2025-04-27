import requests
import json
import networkx as nx
import matplotlib.pyplot as plt
from collections import Counter
import math

#Create URLs
RAVELRY_ENDPOINT = "https://api.ravelry.com"
RAVELRY_PATTERNS = f"{RAVELRY_ENDPOINT}/patterns/search.json"
RAVELRY_SHOPS = f"{RAVELRY_ENDPOINT}/shops/search.json"
RAVELRY_YARNS = f"{RAVELRY_ENDPOINT}/yarns/search.json"
auth= ("", "") #Enter your Ravelry API key here. Should be ("basic auth username", "basic auth password"). Go to https://www.ravelry.com/pro/developer to get a key.
GEOCODE_KEY = ""  #Enter your Geocoding API key here. Should be "key". Go to https://geocode.maps.co/ to get a key.

class Pattern:
    def __init__(self, id, name, free, link, designer):
        """Initializes pattern class with ID, name, free (True or False), designer, and a string version of the information."""
        self.id = id
        self.name = name
        self.free = free
        self.link = link
        self.designer = designer
        self.info = f"Pattern ID: {self.id}\nPattern Name: {self.name}\nPattern Designer: {self.designer}\nPattern Link: {self.link}"
    
    def getFullData(self):
        """Retrieves additional data for a given pattern from the Ravelry API, including the price and currency, the IDs of the recommended yarns, and the category of the pattern (e.g. sweater, scarf, hat, etc.). It then updates the self.info attribute to include this information"""
        response = requests.get(f"{RAVELRY_ENDPOINT}/patterns/{self.id}.json", auth=auth)
        data = response.json()["pattern"]
        self.currency = data.get("currency")
        self.price = data.get("price")
        recYarn = data.get("packs")
        self.recyarn = []
        if recYarn:
            for item in recYarn:
                self.recyarn.append(item.get("yarn_id"))
        category = data.get("pattern_categories")
        self.category = []
        if category:
            for item in category:
                self.category.append(item.get("name"))
        self.info = f"Pattern ID: {self.id}\nPattern Name: {self.name}\nPattern Designer: {self.designer}\nPattern Link: {self.link}\nPattern Recommended Yarns by ID: {self.recyarn}\nPattern Category: {self.category}\nPattern Price: {self.price} {self.currency}"
    
    def getInfo(self):
        """Returns string object with information about a pattern"""
        return self.info

class Shop:
    def __init__(self, id, name, lat, long, city):
        """Initializes shop object with ID, name, latitude, longitude, city, and string with this information."""
        self.id = id
        self.name = name
        self.lat = lat
        self.long = long
        self.city = city
        self.info = f"Shop ID: {self.id}\nShop Name: {self.name}\nShop City: {self.city}"
    
    def getInfo(self):
        """Returns string object with information about shop."""
        return self.info
    
    def calcDistance(self, otherlat, otherlong):
        """Calculates distance between the shop and another set of coordinates using the Haversine formula."""
        R = 3963.1 #radius of earth in miles
        dLat = (float(self.lat)-float(otherlat))*(math.pi/180)
        dLong = (float(self.long)-float(otherlong))*(math.pi/180)
        a = (math.sin(dLat/2)*math.sin(dLat/2)) + math.cos(float(self.lat)*(math.pi/180)) * math.cos(float(otherlat)*(math.pi/180)) * (math.sin(dLong/2)*math.sin(dLong/2))
        d = 2 * math.asin(math.sqrt(a)) * R
        return d

class Yarn:
    def __init__(self, id, name, brand, weight):
        """Initializes yarn object with ID, name, brand, weight, and string with this information."""
        self.id = id
        self.name = name
        self.brand = brand
        self.weight = weight
        self.info = f"Yarn ID: {self.id}\nYarn Name: {self.name}\nYarn Brand: {self.brand}\nYarn Weight: {self.weight}"
    
    def getFullData(self):
        """Retrieves additional data for given yarn from the Ravelry API, specifically the fiber content, and adds it to the info attribute."""
        response = requests.get(f"{RAVELRY_ENDPOINT}/yarns/{self.id}.json", auth=auth)
        data = response.json()["yarn"]
        fibers = data.get("yarn_fibers")
        yarnfibers = []
        if fibers:
            for fiber in fibers:
                fiberDetails = {}
                fiberDetails["percentage"] = fiber.get("percentage")
                fiberDetails["fiber"] = fiber.get("fiber_type")
                yarnfibers.append(fiberDetails)
        self.fiberContent = []
        for fiber in yarnfibers:
            percentage = fiber.get("percentage")
            material = fiber.get("fiber", {}).get("name")
            self.fiberContent.append(f"{percentage}% {material}")

        self.info = f"Yarn ID: {self.id}\nYarn Name: {self.name}\nYarn Brand: {self.brand}\nYarn Weight: {self.weight}\nYarn Fiber Content:{self.fiberContent}"
    
    def getInfo(self):
        """Returns information string for yarn."""
        return self.info
    
    def getMainFiber(self):
        """Finds the main fiber in a given yarn by determining which fiber has the highest percentage. If no percentages are listed, the main fiber is determined to be the first fiber listed."""
        mainFiber = None
        highestpct = 0
        for content in self.fiberContent:
            parts = content.split('%')
            if parts[0].strip() in ("None", None, "null"):
                continue
            elif parts[0].strip() and int(parts[0].strip()):
                pct = int(parts[0].strip())
            else:
                continue
            fiber = parts[1].strip().title()
            if pct and pct >= highestpct:
                highestpct = pct
                mainFiber = fiber
        if not mainFiber:
            parts = self.fiberContent[0].split('%')
            mainFiber = parts[1].strip().title()
        return mainFiber

class Graph:
    def __init__(self, patternsCache = None, shopsCache = None, yarnsCache = None):
        """Initializes graph object by either reading in data from cache or fetching data from Ravelry API. Creates pattern object for each pattern and stores them in self.patterns. Creates yarn object for each yarn and stores them in self.yarns. Creates shop object for each shop and stores them in self.shops."""
        if patternsCache:
            self.patterns = self.loadCache(patternsCache, "pattern")
        else:
            patterns = self.fetchPatternData(RAVELRY_PATTERNS)
            self.patterns = []
            for pattern in patterns:
                patternNode = Pattern(id=pattern.get("id"), name=pattern.get("name").strip().title(), free=pattern.get("free"), link=f"https://www.ravelry.com/patterns/library/{pattern.get("permalink")}", designer = pattern.get("designer", {}).get("name").strip().title())
                self.patterns.append(patternNode)
        if shopsCache:
            self.shops = self.loadCache(shopsCache, "shop")
        else:
            shops = self.fetchShopsData(RAVELRY_SHOPS)
            self.shops = []
            for shop in shops:
                shopNode = Shop(id=shop.get("id"), name=shop.get("name").strip().title(), lat = shop.get("latitude"), long = shop.get("longitude"), city = shop.get("city"))
                self.shops.append(shopNode)
        if yarnsCache:
            self.yarns = self.loadCache(yarnsCache, "yarn")
        else:
            yarns = self.fetchYarnsData(RAVELRY_YARNS)
            self.yarns = []
            for yarn in yarns:
                yarnNode = Yarn(id=yarn.get("id"), name=yarn.get("name").strip().title(), brand=yarn.get("yarn_company_name").strip().title(), weight=yarn.get("yarn_weight"))
                self.yarns.append(yarnNode)

    def fetchPatternData(self, url):
        """Retrieves patterns data from Ravelry API."""
        dataList = []
        response = requests.get(url, auth=auth)
        data = response.json()
        for i in range(int(data["paginator"]["page_count"])):
            response = requests.get(f"{url}?page={i+1}", auth=auth)
            data = response.json()
            dataList.extend(data["patterns"])
        return dataList
    
    def fetchShopsData(self, url):
        """Retrieves shops data from Ravelry API."""
        dataList = []
        response = requests.get(url, auth=auth)
        data = response.json()
        for i in range(int(data["paginator"]["page_count"])):
            response = requests.get(f"{url}?page={i+1}", auth=auth)
            data = response.json()
            dataList.extend(data["shops"])
        return dataList

    def fetchYarnsData(self, url):
        """Retrieves yarns data from Ravelry API."""
        dataList = []
        response = requests.get(url, auth=auth)
        data = response.json()
        for i in range(int(data["paginator"]["page_count"])):
            response = requests.get(f"{url}?page={i+1}", auth=auth)
            data = response.json()
            dataList.extend(data["yarns"])
        return dataList
    
    def cacheData(self, list, filepath):
        """Caches data in a given file"""
        data = []
        for object in list:
            data.append(object.__dict__)
        with open(filepath, "w") as file:
            json.dump(data, file)
    
    def loadCache(self, fileName, type):
        """Loads data from cache file and creates objects of the class of the type of data cached."""
        if fileName:
            with open(fileName, "r") as file:
                object_data = json.load(file)
            if type == "pattern":
                data = [Pattern(id=object.get("id"), name=object.get("name").strip().title(), free=object.get("free"), link=object.get("link"), designer = object.get("designer").strip().title()) for object in object_data]
            elif type == "shop":
                data = [Shop(id=object.get("id"), name=object.get("name").strip().title(), lat = object.get("lat"), long = object.get("long"), city = object.get("city")) for object in object_data]
            elif type == "yarn":
                data = [Yarn(id=object.get("id"), name=object.get("name").strip().title(), brand=object.get("brand").strip().title(), weight=object.get("weight")) for object in object_data]
            return data
        else:
            return False
    
    def getPattern(self, id=None, name=None):
        """Gets full data for a given pattern"""
        if id:
            for pattern in self.patterns:
                if pattern.id == id:
                    print(f"Found {pattern.name}!")
                    pattern.getFullData()
                    yarnList = []
                    for i in range(len(pattern.recyarn)):
                        for yarn in self.yarns:
                            if pattern.recyarn[i] == yarn.id:
                                yarnList.append(f"{yarn.brand} {yarn.name}")
                    return f"{pattern.getInfo()}\nRecommended Yarns by Name: {yarnList}"
            return "Sorry, we couldn't find your pattern."
        elif name:
            for pattern in self.patterns:
                if pattern.name == name.title():
                    print(f"Found {pattern.name}!")
                    pattern.getFullData()
                    yarnList = []
                    for i in range(len(pattern.recyarn)):
                        for yarn in self.yarns:
                            if pattern.recyarn[i] == yarn.id:
                                yarnList.append(f"{yarn.name} by {yarn.brand}")
                    return f"{pattern.getInfo()}\nRecommended Yarns by Brand + Name: {yarnList}"
            return "Sorry, we couldn't find your pattern."
        else:
            return False
    
    def getShop(self, id=None, name=None):
        """Gets full data for a given shop"""
        if id:
            for shop in self.shops:
                if shop.id == id:
                    print(f"Found {shop.name}!")
                    shop.getFullData()
                    return shop.getInfo()
        elif name:
            for shop in self.shops:
                if shop.name == name.title():
                    print(f"Found {shop.name}!")
                    shop.getFullData()
                    return shop.getInfo()
        else:
            return False
        
    def getYarn(self, id=None, name=None):
        """Gets full data for a given yarn"""
        if id:
            for yarn in self.yarns:
                if yarn.id == id:
                    print(f"Found {yarn.name}!")
                    yarn.getFullData()
                    return yarn.getInfo()
        elif name:
            for yarn in self.yarns:
                if yarn.name == name.title():
                    print(f"Found {yarn.name}!")
                    yarn.getFullData()
                    return yarn.getInfo()
        else:
            return False
    
    def createYarnGraph(self, designer):
        """Creates a graph showing the relationships between patterns by a given designer and recommended yarns. Also returns 5 most commonly recommended yarns by the designer"""
        print("Creating graph...")
        graph = nx.Graph()
        designerClean = designer.strip().title()

        designerPatterns = []
        for pattern in self.patterns:
            if pattern.designer == designerClean:
                designerPatterns.append(pattern)
        if not designerPatterns:
            print(f"No patterns found for designer: {designerClean}")
            return graph

        designerYarns = []
        for pattern in designerPatterns:
            pattern.getFullData()
            graph.add_node(pattern.name, label=pattern.name, type='pattern')
            for recyarn in pattern.recyarn:
                for yarn in self.yarns:
                    if yarn.id == recyarn:
                        yarnName = f"{yarn.name} by {yarn.brand}"
                        graph.add_node(yarnName, label=yarnName, type='yarn')
                        graph.add_edge(pattern.name, yarnName)
                        designerYarns.append(f"{yarn.name} by {yarn.brand}")
        
        yarnCount = Counter(designerYarns)
        return (graph, yarnCount.most_common(5))
    
    def createShopGraph(self, city):
        """Creates a graph showing the distances between the yarn shops within 50 miles of a given city. Also returns the top 3 most central yarn shops within this radius"""
        cityClean = city.strip().lower()
        KEY = GEOCODE_KEY
        LINK = f"https://geocode.maps.co/search?city={cityClean}&api_key={KEY}"
        response = requests.get(LINK)
        data = response.json()[0]
        cityLat = float(data.get("lat"))
        cityLong = float(data.get("lon"))
        print("Creating graph...")
        graph = nx.Graph()
        for shop in self.shops:
            if shop.lat and shop.long:
                if shop.calcDistance(otherlat=cityLat, otherlong=cityLong) <= 50:
                    graph.add_node(f"{shop.name} ({shop.city})", object=shop, type='shop')

        for shop in graph.nodes():
            for other_shop in graph.nodes():
                if other_shop != shop:
                    graph.add_edge(shop, other_shop, length=graph.nodes[shop]['object'].calcDistance(otherlat=graph.nodes[other_shop]['object'].lat, otherlong=graph.nodes[other_shop]['object'].long))
        
        if len(graph.nodes()) == 0:
            print("There are no yarn shops within a 50 mile radius of this city.")
            return

        degCent = nx.degree_centrality(graph)
        degCent_sorted = dict(sorted(degCent.items(), key=lambda item: item[1],reverse=True))
        topThree = list(degCent_sorted)[:3]

        return (graph, topThree)
    
    def visualizeGraph(self, G, title=None):
        """Visualizes a given graph. Note: shop and yarn have the same colors because they are never in a graph together."""
        print("Visualizing graph...")

        plt.figure(figsize=(12, 12))
        
        color_map = {
            'pattern': '#F3F4F0',
            'yarn': '#EE6E62',
            'shop': '#EE6E62'
        }
        colors = [color_map[G.nodes[node]['type']] for node in G]
        
        pos = nx.spring_layout(G, k=0.3)
        nx.draw(G, pos, 
                with_labels=True, 
                node_color=colors,
                node_size=800,
                font_size=8,
                edge_color='gray')
        
        for node_type, color in color_map.items():
            plt.scatter([], [], c=color, label=node_type)
        plt.legend()
        
        plt.title(title)
        plt.ion()
        plt.show(block=True)
        plt.ioff()

class Interact:
    def __init__(self, shopsCache=None, yarnsCache=None, patternsCache=None):
        """Initializes interaction with Fiber Arts Finder. Creates graph object and loads in cached data or retrieves data from Ravelry API if no cache."""
        print("Welcome to the Fiber Arts Finder!")
        self.graph = Graph(shopsCache=shopsCache, yarnsCache=yarnsCache, patternsCache=patternsCache)
        self.beginInteraction()
        print("Thanks for using the Fiber Arts Finder! Goodbye!")

    def beginInteraction(self):
        """Essentially the homepage of the program. Gives users options for interactions and allows them to exit the program."""
        userIn = input("What would you like to do? Please select an option by typing in the corresponding number\n(1) Get information about a pattern\n(2) Get information about a designer's most commonly recommended yarns\n(3) Find the most centralized yarn shops near a given city\n(4) Find all yarn shops in a city\n(5) Find possible yarn choices for a given pattern\n(6) Get information about a yarn\n(7) Exit Fiber Arts Finder\nMy Choice: ")
        try:
            if int(userIn) and int(userIn) == 1:
                self.optionOne()
            elif int(userIn) and int(userIn) == 2:
                self.optionTwo()
            elif int(userIn) and int(userIn) == 3:
                self.optionThree()
            elif int(userIn) and int(userIn) == 4:
                self.optionFour()
            elif int(userIn) and int(userIn) == 5:
                self.optionFive()
            elif int(userIn) and int(userIn) == 6:
                self.optionSix()
            elif int(userIn) and int(userIn) == 7:
                return
            else:
                print("Please enter a valid response.")
                self.beginInteraction()
        except:
            print("Please enter a valid response.")
            self.beginInteraction()


    def optionOne(self):
        """Users input the ID or name of a pattern. Retrieves data for pattern and prints. Then returns to homepage."""
        userIn = input("Which would you like to enter? Please select an option by typing in the corresponding number\n(1) The ID of a pattern\n(2) The name of a pattern\nMy Choice: ")

        try:
            if int(userIn) and int(userIn) == 1:
                patternID = input("Pattern ID: ")
                if int(patternID):
                    print(self.graph.getPattern(id=int(patternID)))
                    print("Returning to Fiber Arts Finder home...")
                    self.beginInteraction()
                else:
                    print("Please enter a valid response")
                    self.optionOne()

            elif int(userIn) and int(userIn) == 2:
                patternName = input("Pattern Name: ")
                if patternName:
                    print(self.graph.getPattern(name=patternName))
                    print("Returning to Fiber Arts Finder home...")
                    self.beginInteraction()
                else:
                    print("Please enter a valid response.")
                    self.optionOne()
            else:
                print("Please enter a valid response.")
                self.optionOne()
        except:
            print("Please enter a valid response.")
            self.optionOne()

    def optionTwo(self):
        """Users input the name of a designer. Creates and visualizes graph of designer's patterns and recommended yarns and returns most commonly recommended yarns by designer. Then returns to homepage."""
        userIn = input("Designer Name: ")
        self.visualizeYarnNetwork(userIn, title="Mapping Yarns to Patterns")
        print("Returning to Fiber Arts Finder home...")
        self.beginInteraction()

    def optionThree(self):
        """Users input the name of a city. Creates and visualizes graph of yarn shops within 50 miles of the city and returns most central yarn shops in that radius. Then returns to homepage."""
        userIn = input("Please enter the name of a city for which you would like to see a map of surrounding yarn shops.\nCity Name: ").title()
        self.visualizeShopNetwork(title=f"Graph of Local Yarn Shops within 50 miles of {userIn}", city=userIn)
        print("Returning to Fiber Arts Finder home...")
        self.beginInteraction()

    def optionFour(self):
        """Users input the name of a city. Returns names of all yarn shops in the city. Then returns to homepage."""
        userIn = input("Please enter the name of the city in which you would like to see the yarn shops.\nCity Name: ").title()
        shopsInCity = []
        for shop in self.graph.shops:
            if shop.city == userIn:
                shopsInCity.append(shop)
        
        if shopsInCity:
            print(f"Here are all the yarn shops in {userIn}: {[f"{shop.name}" for shop in shopsInCity]}")
            print("Returning to homepage...")
            self.beginInteraction()
        else:
            print(f"We could not find any shops in {userIn}. Please try another city.")
            self.optionFour()


    def optionFive(self):
        """Users input either a pattern name or ID. If pattern is found, finds the recommended yarns and the fiber content and yarn weight for each yarn. Then, finds other patterns by the same designer and their recommended yarns. If a recommended yarn from a different pattern by the same designer has the same main fiber and yarn weight as one of the recommended yarns, it is added to a list of alternative yarns. This list of alternative yarns is then returned to the user. After all this, it returns to the homepage."""
        userIn = input("Which would you like to enter? Please select an option by typing in the corresponding number\n(1) The ID of a pattern\n(2) The name of a pattern\nMy Choice: ")
        try:
            userIn = int(userIn)
        except:
            userIn = userIn
        if not (isinstance(userIn, int)):
            print("Please enter a valid response.")
            self.optionFive()
        if int(userIn) == 1:
            patternID = input("Pattern ID: ")
            try:
                patternID = int(patternID)
                target_pattern = None
                
                # Find the target pattern
                for pattern in self.graph.patterns:
                    if pattern.id == patternID:
                        print(f"Found {pattern.name}!")
                        target_pattern = pattern
                        break
                
                if not target_pattern:
                    print("Pattern not found")
                    self.beginInteraction()
                    return
            
                # Rest of the logic is the same as ID version
                target_pattern.getFullData()
                pattern_designer = target_pattern.designer

                recommended_yarns = []
                main_fibers = []
                recommended_yarnweights = []
                for yarn_id in target_pattern.recyarn:
                    for yarn in self.graph.yarns:
                        if yarn.id == yarn_id:
                            yarn.getFullData()
                            mainFiber = yarn.getMainFiber()
                            recommended_yarns.append(yarn)
                            main_fibers.append(mainFiber)
                            recommended_yarnweights.append(yarn.weight)
                if recommended_yarns:
                    print("Found recommended yarns!")
                else:
                    print("No recommended yarns found for this pattern")
                    self.beginInteraction()
                    return
                
                similar_patterns = []
                for pattern in self.graph.patterns:
                    if (pattern.designer == pattern_designer and pattern.id != target_pattern.id):
                        pattern.getFullData()
                        similar_patterns.append(pattern)
                print(f"Found other patterns by {pattern_designer}!")

                alternative_yarns = set()
                for pattern in similar_patterns:
                    if not hasattr(pattern, 'recyarn'):
                        continue
                    for yarn_id in pattern.recyarn:
                        if yarn_id is None:
                            continue
                        for yarn in self.graph.yarns:
                            if yarn.id == yarn_id:
                                yarn.getFullData()
                                main_fiber = yarn.getMainFiber()
                                if (main_fiber in main_fibers and yarn.weight in recommended_yarnweights and yarn not in recommended_yarns):
                                    print("Found an alternative yarn")
                                    alternative_yarns.add(f"{yarn.name} by {yarn.brand}")
                
                print(f"{pattern_designer} recommends these yarns for this pattern: {[f"{yarn.name} by {yarn.brand}" for yarn in recommended_yarns]}")
                
                if alternative_yarns:
                    print(f"\nAlternative yarns used in similar patterns: {alternative_yarns}")
                else:
                    print("\nNo alternative yarns found in similar patterns")
            
                self.beginInteraction()
                
            except ValueError:
                print("Please enter a valid pattern ID")
                self.optionFive()

        elif int(userIn) == 2:
            patternName = input("Pattern Name: ").title()
            target_pattern = None
            
            # Find the target pattern
            for pattern in self.graph.patterns:
                if pattern.name == patternName:
                    print(f"Found {patternName}!")
                    target_pattern = pattern
                    break
            
            if not target_pattern:
                print("Pattern not found")
                self.beginInteraction()
                return
            
            # Rest of the logic is the same as ID version
            target_pattern.getFullData()
            pattern_designer = target_pattern.designer

            recommended_yarns = []
            main_fibers = []
            recommended_yarnweights = []
            for yarn_id in target_pattern.recyarn:
                for yarn in self.graph.yarns:
                    if yarn.id == yarn_id:
                        yarn.getFullData()
                        mainFiber = yarn.getMainFiber()
                        recommended_yarns.append(yarn)
                        main_fibers.append(mainFiber)
                        recommended_yarnweights.append(yarn.weight)
            if recommended_yarns:
                print("Found recommended yarns!")
            else:
                print("No recommended yarns found for this pattern")
                self.beginInteraction()
                return
                
            similar_patterns = []
            for pattern in self.graph.patterns:
                if (pattern.designer == pattern_designer and pattern.id != target_pattern.id):
                    pattern.getFullData()
                    similar_patterns.append(pattern)
            print(f"Found other patterns by {pattern_designer}!")

            alternative_yarns = set()
            for pattern in similar_patterns:
                if not hasattr(pattern, 'recyarn'):  # Skip if no recyarn attribute
                        continue
                for yarn_id in pattern.recyarn:
                    if yarn_id is None:  # Skip None values
                        continue
                    for yarn in self.graph.yarns:
                        if yarn.id == yarn_id:
                            yarn.getFullData()
                            main_fiber = yarn.getMainFiber()
                            if (main_fiber in main_fibers and yarn.weight in recommended_yarnweights and yarn not in recommended_yarns):
                                print("Found an alternative yarn")
                                alternative_yarns.add(f"{yarn.name} by {yarn.brand}")
            
            print(f"{pattern_designer} recommends these yarns for this pattern: {[f"{yarn.name} by {yarn.brand}" for yarn in recommended_yarns]}.")
                
            if alternative_yarns:
                print(f"\nAlternative yarns used in similar patterns: {alternative_yarns}")
            else:
                print("\nNo alternative yarns found in similar patterns")
            
            self.beginInteraction()
            
        else:
            print("Please enter 1 or 2")
            self.optionFive()

    def optionSix(self):
        """Users can input the name or ID of a yarn and get detailed information about the yarn, including name, ID, brand, weight, and fiber content."""
        userIn = input("Which would you like to enter? Please select an option by typing in the corresponding number\n(1) The ID of a yarn\n(2) The name of a yarn\nMy Choice: ")

        try:
            if int(userIn) and int(userIn) == 1:
                yarnID = input("Yarn ID: ")
                if int(yarnID):
                    print(self.graph.getYarn(id=int(yarnID)))
                    print("Returning to Fiber Arts Finder home...")
                    self.beginInteraction()
                else:
                    print("Please enter a valid response")
                    self.optionSix()

            elif int(userIn) and int(userIn) == 2:
                yarnName = input("Yarn Name: ")
                if yarnName:
                    print(self.graph.getYarn(name=yarnName))
                    print("Returning to Fiber Arts Finder home...")
                    self.beginInteraction()
                else:
                    print("Please enter a valid response.")
                    self.optionSix()
            else:
                print("Please enter a valid response.")
                self.optionSix()
        except:
            print("Please enter a valid response.")
            self.optionSix()

    def cacheAllData(self, shopsfile, yarnsfile, patternsfile):
        """Caches all data in given file names"""
        self.graph.cacheData(self.graph.shops, shopsfile)
        self.graph.cacheData(self.graph.yarns, yarnsfile)
        self.graph.cacheData(self.graph.patterns, patternsfile)
    
    def visualizeYarnNetwork(self, designer, title=None):
        """Visualizes network connecting patterns and recommended yarns and returns top 5 recommended yarns by the designer."""
        yarnGraph = self.graph.createYarnGraph(designer)
        G = yarnGraph[0]
        if len(G.nodes()) == 0:
            print(f"No data found for designer: {designer}")
            self.beginInteraction()
            return
        print(f"Graph created with {len(G.nodes())} nodes and {len(G.edges())} edges")
        self.graph.visualizeGraph(G, title)
        print(f"Top 5 Recommended Yarns by {designer}: {yarnGraph[1]}")
        self.beginInteraction()
    
    def visualizeShopNetwork(self, title, city):
        """Visualizes network connecting yarn shops within 50 miles of a given city and returns top 3 most central shops within the radius."""
        shopGraph = self.graph.createShopGraph(city)
        G = shopGraph[0]
        print(f"Graph created with {len(G.nodes())} nodes and {len(G.edges())} edges")
        self.graph.visualizeGraph(G, title)
        print(f"Top 3 Most Central Yarn Shops near {city}: {shopGraph[1]}")
        self.beginInteraction()


def main():
    fiber_arts_finder = Interact() #add cached data as attributes here if you have already made the API calls to retrieve data from Ravelry
    fiber_arts_finder.cacheAllData(shopsfile="", yarnsfile="", patternsfile="") #Enter file names to cache data after running for the first time. It takes a longggg time for all the API calls (1-2 hours I think), so definitely cache the data if you want to run it againc

if __name__ == '__main__':
    main()