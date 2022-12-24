from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from enum import Enum
import re
import pandas as pd
import time

RIGHT = True
LEFT = False

# Activate webdriver and gain access to goblinbet
def InitializeGoblinDriver(Visible=False):
    # Set whether to display selium browser
    options = Options()
    # If not visible do not display browser to user
    if not Visible: options.add_argument('--headless')

    url = "https://goblin.bet/#/"
    driver = webdriver.Firefox(options=options)
    driver.get(url)
    # Click button to get through initial prompt
    contButt = WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.CLASS_NAME, "WelcomeStart.Left"))
    contButt.click()
    return driver

# Code to get websites action log, returns a list
def getLog(soup: BeautifulSoup):
    log = []
    # Find log
    logSoup = soup.find("div", {"class": "scrollhost BLogScroll"})

    # If print log true print out the log
    for lg in logSoup.find_all("div", {"class": "LogText"}):
        log.append(lg.text)
    # return the betting log
    return log

# Get users current money
def getMoney(soup: BeautifulSoup):
    return soup.find('span', {"class": "BetsScore"}).text

# Get soup object of a specific creature
def getCreatureSoup(soup: BeautifulSoup, side=LEFT):
    if side == LEFT:
        return soup.find("div", {"class": "Block Statsheet Left TeamRed"})
    return soup.find("div", {"class": "Block Statsheet Right TeamBlue"})

# Strips all alphabetic characters
def stripChrs(word):
    return re.sub("[^0-9]", '', word)

# Strips all nonalphanumeric characters in string
def stripInts(word):
    return re.sub(r'\W+', '', word)

# Finds a tag with a specfic class name
def findSpanClass(soup, className, all=False):
    if not all:
        return soup.find("span", {"class": className})
    return soup.find_all("span", {"class": className})


# Class containing all betting creature information 
class Creature:

    def __init__(self, soup: BeautifulSoup, side=LEFT):
        self.side = side
        self.soup = getCreatureSoup(soup, side)
        self.trueName = self.InitTrueName(self.soup)
        self.displayName = self.InitDisplayName(self.soup)
        self.desc, self.cr = self.InitDescStats(self.soup)
        self.InitStats()
    
    # Gets display name of the creature
    def InitDisplayName(self, soup: BeautifulSoup):
        return findSpanClass(soup, "SSName").text

    # Get true name of creature
    def InitTrueName(self, soup: BeautifulSoup):
        # Find if the adopted banner exists
        banner =  soup.find("div", {"class": "SSStats"})
        # If banner is empty something went wrong, return banner
        if not banner: return ValueError(banner)
        # If the banner contains a 
        val = banner.find('a')
        if val:
            return banner.find("div").text
        return findSpanClass(soup, "SSName").text
    
    # Intializes description stats and cr rank
    def InitDescStats(self, soup: BeautifulSoup):
        cretInfo = None
        cr = None
        for i, tag in enumerate(soup.find_all('span', {'class': "SSInfo"})):
            if i == 0:
                cretInfo = tag.text
            if i == 1:
                cr = tag.text.split(' ')[1]
        return cretInfo, cr

    def getAction(self, action: BeautifulSoup):
        action = [findSpanClass(action, "ActName").text, findSpanClass(action, "ActDesc").text]
        return action

    # Initializes all stats in the creature sheet
    def InitStats(self):
        # Initialize stat categories
        self.stats = None
        self.immunities = None
        self.resists = None
        self.actions = None
        self.conditions = None
        self.wins = None

        # Gets list of all tags in the stats soup
        statsList =  self.soup.find("div", {"class": "SSStats"})
        # Go through every header value in the tags
        for head in statsList.find_all("span", {"class": "SSHeader"}):
            # Record the text of the header
            headTxt = stripInts(head.text)
            if headTxt == "ATTRIBUTES":
                self.stats = self.getAttributes(statsList)
            if headTxt == "WINS":
                self.wins = head.find_next_sibling('span').text.split(',')
            # If content is immunities
            if headTxt == "IMMUNE":
                # Store immunities using next tag
                self.immunities = [word.replace(' ', '') for word in head.find_next_sibling("span").text.split(',')]
            if headTxt == "RESIST":
                # Store resistances using next tag
                self.resists = [word.replace(' ', '') for word in head.find_next_sibling("span").text.split(',')]
            if headTxt == "ACTIONS":
                self.actions = []
                # Append each action to list
                self.InitActions(head)
            if headTxt == "CONDITIONS":
                # Find all conditions
                self.conditions =  self.getConditions(statsList)
            
    # Initializes possible actions of the 
    def InitActions(self, actionHead):
        try:
            child = actionHead
            for action in child.find_next_siblings("div"):
                self.actions.append(self.getAction(action))
            child = child.next
        except AttributeError:
            None

    
    def getConditions(self, statsList: BeautifulSoup):
        conditions = []
        # Highlighted condition
        for tag in findSpanClass(statsList, "Stat Small CanPop Feat"):
            conditions.append(tag.text)
            # Break as the next tag is redundant
            break
        # Loop through all remaining conditions
        for tag in findSpanClass(statsList, "Stat Small", all=True):
            conditions.append(tag.text)

        return conditions


    # Copies attributes tag
    def getAttributes(self, statsList: BeautifulSoup):
        stats = {"STR": None, "DEX": None, "CON": None, "INT": None, "WIS": None, "CHA": None}
        for i, stat in enumerate(statsList.find_all("span", {"class": "Stat"})):
            if i == 0:
                stats["STR"] = stripChrs(stat.text)
            elif i == 1:
                stats["DEX"] = stripChrs(stat.text)
            elif i == 2:
                stats["CON"] = stripChrs(stat.text)
            elif i == 3:
                stats["INT"] = stripChrs(stat.text)
            elif i == 4:
                stats["WIS"] = stripChrs(stat.text)
            elif i == 5:
                stats["CHA"] = stripChrs(stat.text)
            elif i == 6:
                hpVals = [val for val in re.split("/", stat.text)]
                stats["HP"] = stripChrs(hpVals[0])
                stats["HPMax"] = stripChrs(hpVals[1])
            elif i == 7:
                stats["AC"] = stripChrs(stat.text)
            elif i == 8:
                stats["SPD"] = stripChrs(stat.text)
        return stats
    
    # Helper function to return a list from a string delimeted by ','
    def getInfoStrings(self, list):
        if list == None:
            return None
        return ",".join(list)

    # Converts creature action 2d array into a 1d list of strings
    def getActionStrings(self):
        # All action strings are tab delimited
        return "\t".join(["".join(action) for action in self.actions])

    # Returns all information in Creature class as a dictionary
    def getDataLoader(self):
        # Initialize creature dictionary
        cretDict = {"name": self.trueName, "desc": self.desc, "cr": self.cr, "immunities": self.getInfoStrings(self.immunities), 
                    "resists": self.getInfoStrings(self.resists), "conditions": self.getInfoStrings(self.conditions), "wins": self.getInfoStrings(self.wins), "actions": self.getActionStrings(),
                    "hp": self.stats["HPMax"], "str": self.stats["STR"], "dex": self.stats["DEX"], "con": self.stats["CON"], 
                    "int": self.stats["INT"], "wis": self.stats["WIS"], "cha": self.stats["CHA"], "ac": self.stats["AC"],
                    "spd": self.stats["SPD"]}
        return cretDict

                

def saveData(winnerCret: Creature, loserCret: Creature, winnerFile="./DataFrames/Winners.csv", loserFile="./DataFrames/Losers.csv"):
    
    try:
        # initialize winning and losing dataframes
        dfWin = pd.read_csv(winnerFile, index_col=0)
        dfLose = pd.read_csv(loserFile, index_col=0)

        # add new data
        dfWin = pd.concat([dfWin, pd.DataFrame(winnerCret.getDataLoader(), index=[0])], ignore_index=True)
        dfLose = pd.concat([dfLose, pd.DataFrame(loserCret.getDataLoader(), index=[0])], ignore_index=True)

        # Error check
        if len(dfWin) != len(dfLose):
            print("Error discreprancy in data")
            return
        dfWin.to_csv(winnerFile)
        dfLose.to_csv(loserFile)
    except FileNotFoundError:
        # Initialize new dataframes
        dfWin = pd.DataFrame(winnerCret.getDataLoader(), index=[0])
        dfLose = pd.DataFrame(loserCret.getDataLoader(), index=[0])
        # Save to file
        dfWin.to_csv(winnerFile)
        dfLose.to_csv(loserFile)



if __name__ == "__main__":
    driver = InitializeGoblinDriver(False)
    
    try:
        prevLog = []

        while True:# Get Soup

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            
            if soup != None:
                # Gets current log
                log = getLog(soup)
                if len(log) <= 0:
                    continue
                currentEntry = log[0]
                

                # Check if logIsEqual
                if prevLog != log and prevLog != None and log != None:
                    # Prints current entry
                    print(currentEntry)
                    # Check for winner
                    if "eliminated!" in currentEntry:
                        # Initialize creatures
                        cretR = Creature(soup, side=RIGHT)
                        cretL = Creature(soup)

                        if cretR.displayName + " wins!" in currentEntry:
                            saveData(winnerCret=cretR, loserCret=cretL)
                        elif cretL.displayName + " wins!" in currentEntry:
                            saveData(winnerCret=cretL, loserCret=cretR)
                        else:
                            print("Expected creature name, got nothing")
                prevLog = log
            time.sleep(0.9)
    # If cell is interupted save data to csvs
    except KeyboardInterrupt:
        print("====Exiting Program====")