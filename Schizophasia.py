import os
import os.path
import json
import shutil
import random
import sys

random.seed()

class Word:
    def __init__(self, body):
        self.body = body
        self.count = 1
        self.prevWords = {}
        self.isNoun = False
        self.sums = {}


    def increaseCount(self):
        self.count += 1

    
    def addNextWord(self, nextWord, prevWords, deep = -1):
        """gets next word, 
        list of previos words(or one word; including current word) 
        and remembers min(len(prevWords), deep) of it. """
        
        prevWords = [prevWords] if isinstance(prevWords, str) else prevWords
        deep = len(prevWords) if deep < 0 else min(deep, prevWords)
        first = len(prevWords) - deep
        for i in range(first, len(prevWords)):
            prevSequence = ' '.join(prevWords[i:]).lower()
            self.prevWords[prevSequence] = self.prevWords.get(prevSequence, {})
            self.sums[prevSequence] = self.sums.get(prevSequence, 0) + 1
            nextWordCounts = self.prevWords[prevSequence]
            nextWordCounts[nextWord] = nextWordCounts.get(nextWord, 0) + 1

    
            
    def fromJsonObject(self, obj):
        self.body = obj["body"]
        self.count = obj["uses"]
        self.prevWords = obj["nexts"]
        self.sums = obj["sums"]


    def getNextWord(self, prevWords, 
                    randomFunc = lambda a: random.randint(0, a)):
        """gets list of previos words(or one word; including current word)
        and counts next word using min(len(words), deep) of previous. 
        You can use own random function(a) - returns random 0 <= n <= a.
        Frequent words are in the begin.
        Returns next word in lower case"""
        
        exPrevWords = prevWords
        prevWords = prevWords.lower() if isinstance(prevWords, str) else ' '.join(prevWords).lower()
        nextWordCounts = self.prevWords[prevWords].items()
        nextWordCounts.sort(key = lambda (a, b): -b)

        wordNum = randomFunc(self.sums[prevWords])
        currendWordCount = 0
        for counts in nextWordCounts:
            currendWordCount += counts[1]
            if currendWordCount >= wordNum:
                return counts[0]

        return nextWordCounts[0][0]




class WordsDictionary:
    def __init__(self):
        self.body = {}
        self.size = 0
        self.lastWord = Word('')
        self.parafraphCounter = Word('')

    def pushWord(self, nextWord, lastWords):
        isNoun = (not self.isPunctMark(nextWord) and nextWord.istitle() and 
                  len(lastWords) > 0 and 
                  not self.isSentanceTerminator(lastWords[-1]))
        if self.body.has_key(nextWord.lower()):
            self.body[nextWord.lower()].increaseCount()
        else:
            self.body[nextWord.lower()] = Word(nextWord)

        self.lastWord.addNextWord(nextWord, lastWords[-self.deep:])
        self.lastWord = self.body[nextWord.lower()]
        self.size += 1


    def readWordsGetter(self, getter):
        lastWords = []
        word = wordsGetter.getWord()
        nSentances = 0
        while word != '':
            if (self.isSentanceTerminator(word)):
                nSentances += 1
            if (word == '\n'):
                self.parafraphCounter.addNextWord(str(nSentances), [''])
                nSentances = 0
            else:
                self.pushWord(word, lastWords)
                lastWords.append(word)
            word = wordsGetter.getWord()

        for i in range(self.deep):
            word = lastWords[i]
            self.pushWord(word, lastWords)
            lastWords.append(word)

    def _generateParagraph(self, lastWords, length):
        result = []
        lastWords = ['.'] if len(lastWords) == 0 else lastWords
        nSentances = 0
        nWords = 0
        while nSentances < length:
            word = self.body[lastWords[-1]]
            newWord = self.body[word.getNextWord(lastWords[-2:]).lower()]
            
            if not (self.isPunctMark(newWord.body) or newWord.body == '-'):
                result.append(' ')
            elif self.isSentanceTerminator(newWord.body):
                nSentances += 1

            if self.isSentanceTerminator(lastWords[-1]):
                result.append(newWord.body.capitalize())
            else:
                result.append(newWord.body)
            lastWords.append(newWord.body.lower())

            nWords += 1

        return result, lastWords[-self.deep:], nWords


    def generateText(self, length):
        nWords = 0
        result = []
        lastWords = []
        while nWords < length:
            nPars = int(self.parafraphCounter.getNextWord(['']))
            paragraph, lastWords, l = self._generateParagraph(lastWords, nPars)
            nWords += l
            result.extend(paragraph)
            result.append('\n')
            print 'generated: ', nWords, ' words'
        return ''.join(result)


    def _firstStatisticToCsv(self, fileName, sortFunc):
        vals = self.body.values()
        vals.sort(key = sortFunc)
        file = open(fileName, 'w')
        file.write(''.join(['', ', ,', str(self.size), '\n']))
        for i in vals:
            file.write(''.join([i.body, ',', str(i.count), '\n']))
        file.close()

    def _secondStatisticToCsv(self, folderName):
        if os.path.exists(folderName + "/"):
            shutil.rmtree(folderName, ignore_errors=True)
        os.mkdir(folderName + "/")

        for word in self.body.values():
            fName = word.body
            # cause Win names
            # may fail in UNIX
            if fName == "?":
                fName = "$QUESTION$"
            elif fName == 'aux':
                fName = '_aux'
            file = open(''.join([folderName, '/', fName, '.csv']), 'w')
            file.write(''.join(['SUMMARY:', ',', str(word.count), '\n\n']))
            prevItems = word.prevWords.items();
            prevItems.sort(key = lambda a: len(a[0].split(' ')))
            for prevSequence, nextsMap in prevItems:
                vals = nextsMap.items()
                vals.sort(key = lambda a: -a[1])

                for i in vals:
                    file.write(','.join([prevSequence, i[0], str(i[1])]))
                    file.write("\n")
                file.write("\n")

            file.close()


    def toCsv(self, firstFileName, secondFolderName, sortFunc = lambda a: -a.count):
        '''First statistic in fileName. Is like "word, count". 
        
        In folder we create many files for second statistics. Each is 
        "%word%.csv", with "%prevSequence%, %nextWord%, count" rows inside.
        
        By default sorted by count in text.'''
        self._firstStatisticToCsv(firstFileName, sortFunc)
        self._secondStatisticToCsv(secondFolderName)
        

    def toJson(self, fileName):
        result = {}
        for word in self.body:
            result[word] = {
                "body": self.body[word].body,
                "uses": self.body[word].count,
                "nexts": self.body[word].prevWords,
                "sums": self.body[word].sums,
                }

        f = open(fileName, 'w')
        json.dump(result, f)
        f.close()

    
    def fromJson(self, fileName):
        f = open(fileName, 'r')
        content = f.read()
        f.close()
        wordsArr = json.loads(content)
        self.size = 0
        for wordName, jWordObj in wordsArr.items():
            word = Word('')
            word.fromJsonObject(jWordObj)
            self.body[wordName] = word
            self.size += 1


    def __len__(self):
        return self.size

    def isSentanceTerminator(word):
        return word == '.' or word == '...' or word == '?' or word == '!'

    isSentanceTerminator = staticmethod(isSentanceTerminator)
    
 
    def isPunctMark(word):
        return word in ['.', '...', '?', '!', ',', '/', '\\', '|', 
                        '@', '#', '$', '%', '^', ':', ';', '*', '+', '-']

    isPunctMark = staticmethod(isPunctMark)
    
    deep = 2


class FileWordsGetter:
    def __init__(self, fileName):
        self.fileName = fileName
        self._fileOpened = False
        self._pos = 0

    def _readFromFile(self):
        file = open(self.fileName, 'r')
        text = file.read()
        file.close()
        self.words = self._readFromText(text)
        self._fileOpened = True

        
    def _readFromText(self, text):
        result = []
        lastWord = ''
        # we can't use for c in text, cause '...'
        # word can contain any letter or be ., !, ?, ...
        i = 0
        while i < len(text):
            c = text[i]
            if c.isalpha() or c in ['`', '-']:
                lastWord += c
            else:
                if lastWord != '':
                    result.append(lastWord)
                lastWord = ''

                if text[i: i+3] == '...':
                    i += 2
                    result.append('...')
                elif WordsDictionary.isPunctMark(c):
                    result.append(c)
                elif c == '\n':
                    result.append(c)
            i += 1
        return result

    def getWord(self):
        if not self._fileOpened:
            self._readFromFile()

        if self._pos >= len(self.words):
            return ''
        else:
            self._pos += 1
            return self.words[self._pos - 1]


class FolderWordsGetter:
    def __init__(self, dirName):
        self.dirName = dirName
        files = self._readFilesInDir(dirName)
        self._pos = 0
        self.getters = [FileWordsGetter(fname) for fname in files]

    def _readFilesInDir(self, dirName):
        result = []
        for root, dirs, files in os.walk(dirName):
            for name in files:
                result.append(''.join([root, '/', name]))
        return result

    def getWord(self):
        if self._pos >= len(self.getters):
            return ''
        result = self.getters[self._pos].getWord()
        while result == '' and self._pos < len(self.getters) - 1:
            self._pos += 1
            print ''.join(['parsed ', str(self._pos - 1), ' of ', str(len(self.getters)),
                           ' (', self.getters[self._pos].fileName, ')'])
            result = self.getters[self._pos].getWord()
        return result



dict = WordsDictionary()

if len(sys.argv) < 3:
    print 'Not enough arguments'
    sys.exit(-1)

if sys.argv[1] == 'fromText':
    folderName = sys.argv[2]
    wordsGetter = FolderWordsGetter(folderName)
    dict.readWordsGetter(wordsGetter)
elif sys.argv[1] == 'fromJson':
    jsonFile = sys.argv[2]
    dict.fromJson(jsonFile)

if sys.argv.count('export') > 0:
    dict.toCsv('firstStatistic.csv', 'secondStatisticCsvs')
    dict.toJson('firstStatistic.json')

out = open('out.txt', 'w')
out.write(dict.generateText(int(sys.argv[3])))
out.close()

