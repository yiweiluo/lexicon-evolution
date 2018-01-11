import bs4
import numpy
import requests
from sense import *
from math import exp
from numpy import mean
numpy.seterr(all='raise')
import scipy.stats as stats

class Word:

    def __init__(self, word, part_of_speech="all"):
        self.label = word
        self.PoS = part_of_speech
        self.senses = self.make_sense_list(word, part_of_speech)
        self.length = len(self.senses)
        self.viable = True  #becomes false when the word has correlations that are not viable, or has no non-baseline senses
        if len(self.senses) <= 1: #or self.senses[0].date == self.senses[-1].date:
            self.bl_senses = self.senses
            self.nb_senses = []
            self.start_date = self.senses[0].date
        else:
            index = 0
            while True:
                if index >= self.length:
                    break
                if self.senses[index].date != self.senses[index+1].date:
                    break
                index += 1
            self.bl_senses = self.senses[:index+1:]
            self.nb_senses = self.senses[index+1::]
            if self.senses:
                self.avg_externality = mean([float(sense.externality) for sense in self.bl_senses])
                if self.avg_externality > 0.50:
                    self.externality = 1
                else:
                    self.externality = 0
        self.frequency = 0 #not used initially


        if self.nb_senses:
            self.num_nb_senses = len(self.nb_senses)
            self.num_bl_senses = self.length - self.num_nb_senses
            self.num_senses = self.num_nb_senses + self.num_bl_senses
            self.num_exist_senses = len([s for s in self.senses if s.end_date == 3000])
            self.nb_dates = [nb_sense.date for nb_sense in self.nb_senses]
            self.vs_baseline = [Baseline(bl_sense, self.nb_senses) for bl_sense in self.bl_senses]  #list of baseline senses
            self.vs_baseline = [baseline for baseline in self.vs_baseline if baseline.pearsonR]
            """
            #self.tests = [stats.pearsonr(bl_sense.nb_dates, bl_sense.sim_scores)[0] for bl_sense in self.vs_baseline]
            #self.ptests = [stats.pearsonr(bl_sense.nb_dates, bl_sense.sim_scores)[1] for bl_sense in self.vs_baseline]
            self.x = sum(self.tests) / float(len(self.vs_baseline))
            self.y = sum(self.ptests) / float(len(self.vs_baseline))

            #Calculate the Pearson R with averaging after
            try:
                self.pearsons = [numpy.corrcoef(bl_sense.nb_dates, bl_sense.sim_scores).tolist()[0][1] for bl_sense in self.vs_baseline]
                #self.probs = [numpy.corrcoef(bl_sense.nb_dates, bl_sense.sim_scores).tolist()[0][1] for bl_sense in self.vs_baseline]
            except:
                self.viable = False
            try:
                self.pearson_avg_after = sum(self.pearsons)/float(len(self.vs_baseline))
                self.probs_avg_after = sum(self.probs) / float(len(self.vs_baseline))
            except:
                self.viable = False

            #Calculate the Pearson R with averaging before
            scores_by_date = numpy.transpose([bl.sim_scores for bl in self.vs_baseline])    #turns scores sorted by baseline sense into scores sorted by date
            try:
                self.avgs_by_date = [sum(scores)/float(len(scores)) for scores in scores_by_date]
            except:
                self.viable = False
            try:
                self.pearson_avg_before = numpy.corrcoef(self.nb_dates, self.avgs_by_date)[0][1]
            except:
                self.viable = False
        else:
            self.viable = False #there are no sense to compare against the baseline

        """

    def make_sense_list(self, label, part_of_speech):
        """Takes a word and searches for it within the HTE database,
        returning a list with the same information in a sense
        object with, ordered a date, word_form, identifiers, and
        categories"""

        if part_of_speech == "a":
            part_of_speech = "aj"
        if part_of_speech == "adv":
            part_of_speech = "av"

        if part_of_speech == "v":
            url = "http://historicalthesaurus.arts.gla.ac.uk/category-selection/?word=" + label + "&pos%5B%5D=allv&pos%5B%5D=v&pos%5B%5D=vi&pos%5B%5D=vm&pos%5B%5D=vp&pos%5B%5D=vr&pos%5B%5D=vt&label=&category=&startf=&endf=&startl=&endl="
        elif part_of_speech == "all":
            url = "http://historicalthesaurus.arts.gla.ac.uk/category-selection/?word=" + label + "&label=&category=&startf=&endf=&startl=&endl="
        else:
            url = "http://historicalthesaurus.arts.gla.ac.uk/category-selection/?word=" + label + "&pos%5B%5D=" + part_of_speech + "&label=&category=&startf=&endf=&startl=&endl="

        r = requests.get(url)
        soup = bs4.BeautifulSoup(r.content, "html.parser")
        for a in soup.find_all("a"):
            del a['href']

        catOdds, catEvens = soup.find_all("p", "catOdd"), soup.find_all("p", "catEven")
        allCat = catOdds + catEvens

        sense_list = []

        for index in range(0, len(allCat)):
            indexed_sense = Sense(label, allCat, index)
            # Skip past the current selection if the date is not a starting date
            if not indexed_sense.date:
                continue
            sense_list.append(indexed_sense)

        # this separation is done so that we can sort the list with OE at the beginning instead of the end
        OE_list = [sense for sense in sense_list if sense.date == "OE"]
        non_OE_list = [sense for sense in sense_list if sense.date != "OE"]
        sense_list = OE_list + sorted(non_OE_list, key=lambda x: x.date)

        return sense_list

    def __repr__(self):
        return self.label

    def __str__(self):
        return self.label

class Baseline:

    def __init__(self, bl_sense, nb_senses):
        self.bl_sense = bl_sense
        self.nb_senses = nb_senses
        self.nb_dates = [nb_sense.date for nb_sense in nb_senses]
        self.sim_scores = [self.calculate_score(bl_sense, nb_sense) for nb_sense in nb_senses]
        try:
            self.pearsonR = numpy.corrcoef(self.nb_dates, self.sim_scores).tolist()[0][1]
        except:
            self.pearsonR = False

    def calculate_score(self, bl_sense, nb_sense):
        similarity_score = 0
        list_range = min(len(bl_sense.listed_cat), len(nb_sense.listed_cat))
        for r in range(list_range):
            if bl_sense.listed_cat[r] == nb_sense.listed_cat[r]:
                similarity_score += 1
            else:
                break
        return exp(-similarity_score)
