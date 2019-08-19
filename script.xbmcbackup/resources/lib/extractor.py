import utils as utils

class ZipExtractor:
    
    def extract(self,zipFile,outLoc,progressBar):
        utils.log("extracting zip archive")
        
        result = True #result is true unless we fail
        
        #update the progress bar
        progressBar.updateProgress(0,utils.getString(30100))
        
        #list the files 
        fileCount = float(len(zipFile.listFiles()))
        currentFile = 0
        
        try:
            for aFile in zipFile.listFiles():
                #update the progress bar
                currentFile += 1
                progressBar.updateProgress(int((currentFile/fileCount) * 100),utils.getString(30100))
                
                #extract the file
                zipFile.extract(aFile,outLoc)
                
        except Exception as e:
            utils.log("Error extracting file")
            result = False
            
        return result
                
