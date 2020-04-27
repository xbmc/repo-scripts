# -*- coding: utf-8 -*-

def getQuerySeries():
	return querySeries
def getQueryEpisodes():
	return queryEpisodes + fragmentVideoItems_programme
def getQueryCategories():
	return queryCategories
def getQueryVideo():
	return queryVideo
def getQueryBoards():
	return 
def getQueryBoard():
	return queryBoard + fragmentClip
def getQueryGenres():
	return queryGenres
def getQueryAllClips():
	return query_allClips + fragmentVideoItems_clip + fragmentClip
def getQuerySections():
	return querySections
def getQuerySection():
	return querySection + fragmentClip
def getQueryDate():
	return queryDate

	
	

#TODO Make audioOnly a variable
querySeries = """{
  viewer {
    allSeries(first:1000,filter:{audioOnly: {eq: false}}) {
      edges {
        node {
          id
          title
          kicker
          description
          shortDescription
          defaultTeaserImage {
            imageFiles {
              edges {
                node {
                  publicLocation
                }
              }
            }
          }
        }
      }
    }
  }
}"""

#      episodes(last:200,filter:{broadcasts:{empty:{eq:false}},availableUntil:{gte:"2018-05-27T17:30:00.000Z"},essences:{empty:{eq:false}}}) {
#      episodes(last:200,filter:{broadcasts:{empty:{eq:true}},essences:{empty:{eq:false}}}) {
#      episodes(last:200,filter:{broadcasts:{empty:{eq:false}},essences:{empty:{eq:false}}}) {
#queryEpisodes = """query episodes($day: Day!, $id:ID!)
queryEpisodes = """query episodes($id:ID!, $day: DateTime!)
{
  viewer {
    series(id:$id) {
      episodes(last:200,filter:{availableUntil:{gte:$day},essences:{empty:{eq:false}}},orderBy:BROADCASTS_CREATEDAT_DESC) {
        ...videoitems_programme
      }
    }
  }
}"""

#av:http://ard.de/ontologies/categories#mittelfranken
queryCategories = """{
  viewer {
    allCategories {
      edges {
        node {
          id
          label
        }
      }
    }
  }
}"""

queryGenres = """{
  viewer {
    allGenres {
      edges {
        node {
          id
          label
        }
      }
    }      
  }
}"""

query_allClips = """query clips($filter: ClipFilter) {
  viewer {
    allClips(filter: $filter) {
      ...videoitems_clip
    }
  }
}"""

#maybe check for cc? new profiles?
queryVideo = """query video($clipId: ID!) {
  viewer {
    clip(id: $clipId) {
      videoFiles(first: 100, filter: {videoProfile: {id: {eq: "av:http://ard.de/ontologies/audioVideo#VideoProfile_HLS"}}}) {
        edges {
          node {
            publicLocation
            subtitles {
              edges {
                node {
                  timedTextFiles(filter: {mimetype: {eq: "application/ttml+xml; codecs=ede1"}}) {
                    edges {
                      node {
                        publicLocation
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

queryBoard = """query video($boardId:ID!)
{
  viewer {
    board(id:$boardId) {
      sections {
        edges {
          node {
            title
            contents {
              edges {
                node {
                  represents {
                    ...clip
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}"""

querySections = """{
  viewer {
    allSections(last:200) {
      edges {
        node {
          id
          title
        }
      }
    }       
  }
}
"""

querySection = """query section($id:ID!)
{
  viewer {
    section(id:$id) {
      id
      contents(last:10) {
        edges {
          node {
            represents{
              ...clip
            }
          }
        }
      }
    } 
  }
}"""


queryDate = """query date($day: Day!, $slots: [EPGSlotKey], $broadcasterId: ID!) {
  viewer {
    allLivestreams(filter: {broadcastedBy: {id: {eq: $broadcasterId}}}) {
      edges {
        node {
          epg(day: $day, slots: $slots) {
            broadcastEvent {
              publicationOf {
                id
                title
                kicker
                shortDescription
                description
                defaultTeaserImage {
                  imageFiles {
                    edges {
                      node {
                        publicLocation
                      }
                    }
                  }
                }
                essences {
                  edges {
                    node {
                      id
                      publicLocation
                    }
                  }
                }
              }
              start
              end
            }
          }
        }
      }
    }
  }
}
"""

###fragments
fragmentVideoItems_programme = """fragment videoitems_programme on ProgrammeConnection{
  edges {
    node {
      id
      title
      kicker
      description
      shortDescription
      ageRestriction
      availableUntil
      episodeNumber
      duration
      defaultTeaserImage {
        imageFiles {
          edges {
            node {
              publicLocation
            }
          }
        }        
      }
    }
  }
}"""

fragmentVideoItems_clip = """

fragment videoitems_clip on ClipConnection{
  edges {
    node {
      ...clip
    }
  }
}"""

fragmentClip = """

fragment clip on ClipInterface {
  id
  title
  kicker
  description
  shortDescription
  ageRestriction
  availableUntil
  duration
  defaultTeaserImage {
    imageFiles {
      edges {
        node {
          publicLocation
        }
      }
    }
  }
}"""


Squery_CategoryPageRendererQuery = """query CategoryPageRendererQuery($nodes: [ID]!) {
  nodes(ids: $nodes) {
    __typename
    node {
      id
    }
    id
  }
}"""