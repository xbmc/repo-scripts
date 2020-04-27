# -*- coding: utf-8 -*-

#import libmediathek3 as libmediathek




def getQueryShows(letter=''):
	return _dependencyBuilder(Dquery_SearchPageQuery)
def getQueryEpisodes():
	return _dependencyBuilder(Dquery_SeriesPageRendererQuery)
def getQueryVideo():#TODO: path
	return Squery_DetailPageRendererQuery
def getQueryDate():
	return _dependencyBuilder(Dquery_ProgrammeContainerRefetchQuery)
def getQueryDate2():#TODO: path
	return _dependencyBuilder(Dquery_ProgrammeCalendarPageRefetchQuery)
def getStart():
	return _dependencyBuilder(Dquery_StartPageQuery)
def getCats():
	return _dependencyBuilder(Dquery_CategoryPageRendererQuery)


def getIntrospectionQuery():#TODO: path
	return Squery_IntrospectionQuery

def _dependencyBuilder(base):
	l = [base[0]]
	for subDep in base[1]:
		l = _addDep(subDep,l)
	
	result = ''
	for s in l:
		result += s
	return result.replace('\\n','').replace('\n','').replace('\r','')
	
def _addDep(dep,l):
	if dep[0] not in l:
		l.append(dep[0])
		for subDep in dep[1]:
			l = _addDep(subDep,l)
	return l

Squery_IntrospectionQuery = """

  query IntrospectionQuery {
    __schema {
      queryType { name }
      mutationType { name }
      subscriptionType { name }
      types {
        ...FullType
      }
      directives {
        name
        description
        args {
          ...InputValue
        }
        onOperation
        onFragment
        onField
      }
    }
  }

  fragment FullType on __Type {
    kind
    name
    description
    fields(includeDeprecated: true) {
      name
      description
      args {
        ...InputValue
      }
      type {
        ...TypeRef
      }
      isDeprecated
      deprecationReason
    }
    inputFields {
      ...InputValue
    }
    interfaces {
      ...TypeRef
    }
    enumValues(includeDeprecated: true) {
      name
      description
      isDeprecated
      deprecationReason
    }
    possibleTypes {
      ...TypeRef
    }
  }

  fragment InputValue on __InputValue {
    name
    description
    type { ...TypeRef }
    defaultValue
  }

  fragment TypeRef on __Type {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
        }
      }
    }
  }"""
	
	
#Strings for queries
Squery_SearchPageQuery = """query SearchPageQuery(
  $letter: String
) { 
  viewer {
    ...Search_viewer
    id
  }
}"""

Squery_SeriesPageRendererQuery = """query SeriesPageRendererQuery(
  $id: ID!
  $itemCount: Int
  $clipCount: Int
  $previousEpisodesFilter: ProgrammeFilter
  $clipsOnlyFilter: ProgrammeFilter
) {
  viewer {
    ...SeriesPage_viewer_2PDDaq
    id
  }
}"""

Squery_DetailPageRendererQuery = """query DetailPageRendererQuery(
  $clipId: ID!
  $isClip: Boolean!
  $isLivestream: Boolean!
  $livestream: ID!
) {
  viewer {
    ...DetailPage_viewer_22r5xP
    id
  }
}

fragment DetailPage_viewer_22r5xP on Viewer {
  ...VideoPlayer_viewer_22r5xP
  detailClip: clip(id: $clipId) {
    __typename
    id
    title
  }
}

fragment VideoPlayer_viewer_22r5xP on Viewer {
  id
  clip(id: $clipId) @include(if: $isClip) {
    __typename
    id
    ageRestriction
    videoFiles(first: 100) {
      edges {
        node {
          __typename
          id
          mimetype
          publicLocation
          videoProfile {
            __typename
            id
            width
          }
        }
      }
    }
    title
    defaultTeaserImage @include(if: $isClip) {
      __typename
      imageFiles(first: 1) {
        edges {
          node {
            __typename
            id
            publicLocation
            crops(first: 1) {
              edges {
                node {
                  __typename
                  publicLocation
                  id
                }
              }
            }
          }
        }
      }
      id
    }
    ... on ProgrammeInterface {
      episodeOf {
        __typename
        defaultTeaserImage @include(if: $isClip) {
          __typename
          imageFiles(first: 1) {
            edges {
              node {
                __typename
                id
                publicLocation
                crops(first: 1) {
                  edges {
                    node {
                      __typename
                      publicLocation
                      id
                    }
                  }
                }
              }
            }
          }
          id
        }
        id
      }
    }
    myInteractions {
      __typename
      completed
      progress
      id
    }
    ...Settings_clip
  }
  livestream(id: $livestream) @include(if: $isLivestream) {
    __typename
    id
    streamingUrls(first: 10, filter: {accessibleIn: {contains: "GeoZone:http://ard.de/ontologies/coreConcepts#GeoZone_World"}, hasEmbeddedSubtitles: {eq: false}}) {
      edges {
        node {
          __typename
          id
          publicLocation
        }
      }
    }
  }
}

fragment Settings_clip on ClipInterface {
  videoFiles(first: 100) {
    edges {
      node {
        __typename
        id
        mimetype
        publicLocation
        videoProfile {
          __typename
          id
          width
          height
        }
      }
    }
  }
}"""

Squery_ProgrammeContainerRefetchQuery = """query ProgrammeContainerRefetchQuery(
  $broadcastServiceId: ID!
  $programmeFilter: ProgrammeFilter!
) {
  viewer {
    broadcastService(id: $broadcastServiceId) {
      __typename
      ...ProgrammeContainer_broadcastService_fYjpM
      id
    }
    id
  }
}"""

Squery_ProgrammeCalendarPageRefetchQuery = """query ProgrammeCalendarPageRefetchQuery($broadcasterId: ID!, $day: Day!, $slots: [EPGSlotKey]) {
  viewer {
    ...ProgrammeCalendarPage_viewer_1qA6ko
    id
  }
}"""

Squery_StartPageQuery = """query StartPageQuery($boardId: ID!) {
  viewer {
    board(id: $boardId) {
      __typename
      ...StartPage_board_4prhdM
      id
    }
    id
  }
}"""

Squery_CategoryPageRendererQuery = """query CategoryPageRendererQuery($nodes: [ID]!) {
  nodes(ids: $nodes) {
    __typename
    ...CategoryPage_nodes
    id
  }
}"""

Squery_BoardPageRendererQuery = """query BoardPageRendererQuery($boardFilter: BoardFilter!) {
  viewer {
    allBoards(first: 1, filter: $boardFilter) {
      edges {
        node {
          __typename
          ...BoardPage_board
          id
        }
      }
    }
    id
  }
}"""


#Strings for fragments

Sfragment_Search_viewer = """

fragment Search_viewer on Viewer {
  ...SeriesIndex_viewer
}"""

#Added: kicker, description, shortDescription
Sfragment_SeriesIndex_viewer = """

fragment SeriesIndex_viewer on Viewer {
  seriesIndexAllSeries: allSeries(first: 1000, orderBy: TITLE_ASC, filter: {title: {startsWith: $letter}, audioOnly: {eq: false}, status: {id: {eq: "Status:http://ard.de/ontologies/lifeCycle#published"}}}) {
    edges {
      node {
        __typename
        id
        title
        kicker
        description
        shortDescription
        ...SeriesTeaserBox_node
        ...TeaserListItem_node
      }
    }
  }
}"""

Sfragment_SeriesTeaserBox_node = """

fragment SeriesTeaserBox_node on Node {
  __typename
  id
  ... on CreativeWorkInterface {
    ...TeaserImage_creativeWorkInterface
  }
  ... on SeriesInterface {
    ...SubscribeAction_series
    subscribed
    title
  }
}
"""
Sfragment_TeaserListItem_node = """

fragment TeaserListItem_node on Node {
  __typename
  id
  ... on CreativeWorkInterface {
    ...TeaserImage_creativeWorkInterface
  }
  ... on ClipInterface {
    title
  }
}"""

Sfragment_TeaserImage_creativeWorkInterface = """

fragment TeaserImage_creativeWorkInterface on CreativeWorkInterface {
  id
  kicker
  title
  teaserImages(first: 1) {
    edges {
      node {
        __typename
        shortDescription
        id
      }
    }
  }
  defaultTeaserImage {
    __typename
    imageFiles(first: 1) {
      edges {
        node {
          __typename
          id
          publicLocation
          crops(first: 10) {
            count
            edges {
              node {
                __typename
                publicLocation
                width
                height
                id
              }
            }
          }
        }
      }
    }
    id
  }
}"""

Sfragment_SubscribeAction_series = """

fragment SubscribeAction_series on SeriesInterface {
  id
  subscribed
}"""


Sfragment_SeriesPage_viewer_2PDDaq = """

fragment SeriesPage_viewer_2PDDaq on Viewer {
  series(id: $id) {
    __typename
    ...TeaserImage_creativeWorkInterface
    ...SeriesBrandBanner_series
    ...ChildContentRedirect_creativeWork
    clipsOnly: episodes(orderBy: VERSIONFROM_DESC, first: $clipCount, filter: $clipsOnlyFilter) {
      ...ProgrammeSlider_programmes
    }
    previousEpisodes: episodes(first: $itemCount, orderBy: BROADCASTS_START_DESC, filter: $previousEpisodesFilter) {
      ...ProgrammeSlider_programmes
      edges {
        node {
          __typename
          ...SmallTeaserBox_node
          id
        }
      }
    }
    id
  }
}"""

Sfragment_SeriesBrandBanner_series = """

fragment SeriesBrandBanner_series on SeriesInterface {
  ...SubscribeAction_series
  title
  shortDescription
  externalURLS(first: 1) {
    edges {
      node {
        __typename
        id
        url
        label
      }
    }
  }
  brandingImages(first: 1) {
    edges {
      node {
        __typename
        imageFiles(first: 1) {
          edges {
            node {
              __typename
              publicLocation
              id
            }
          }
        }
        id
      }
    }
  }
}"""

Sfragment_SubscribeAction_series = """

fragment SubscribeAction_series on SeriesInterface {
  id
  subscribed
}"""

Sfragment_ChildContentRedirect_creativeWork = """

fragment ChildContentRedirect_creativeWork on CreativeWorkInterface {
  categories(first: 100) {
    edges {
      node {
        __typename
        id
      }
    }
  }
}"""

Sfragment_ProgrammeSlider_programmes = """

fragment ProgrammeSlider_programmes on ProgrammeConnection {
  edges {
    node {
      __typename
      ...SmallTeaserBox_node
      id
    }
  }
}"""

#Added: description, shortDescription
Sfragment_SmallTeaserBox_node = """

fragment SmallTeaserBox_node on Node {
  id
  ... on CreativeWorkInterface {
    ...TeaserImage_creativeWorkInterface
  }
  ... on ClipInterface {
    id
    title
    kicker
    description
    shortDescription
    ...Bookmark_clip
    ...Duration_clip
    ...Progress_clip
  }
  ... on ProgrammeInterface {
    broadcasts(first: 1, orderBy: START_DESC) {
      edges {
        node {
          __typename
          start
          id
        }
      }
    }
  }
}"""

Sfragment_Bookmark_clip = """

fragment Bookmark_clip on ClipInterface {
  id
  bookmarked
  title
}"""

Sfragment_Duration_clip = """

fragment Duration_clip on ClipInterface {
  duration
}"""

Sfragment_Progress_clip = """

fragment Progress_clip on ClipInterface {
  myInteractions {
    __typename
    progress
    completed
    id
  }
}"""



###SubtitlesInfo_clip added
Sfragment_ProgrammeTeaserBox_programme = """

fragment ProgrammeTeaserBox_programme on ProgrammeInterface {
  title
  broadcasts(first: 1) {
    edges {
      node {
        __typename
        start
        end
        id
      }
    }
  }
  ... on CreativeWorkInterface {
    ...TeaserImage_creativeWorkInterface
  }
  ... on ClipInterface {
    title
    kicker
    essences(first: 1) {
      count
    }
    ...Bookmark_clip
    ...Duration_clip
    ...SubtitlesInfo_clip
  }
}"""

Sfragment_ProgrammeTableRow_programme = """

fragment ProgrammeTableRow_programme on ProgrammeInterface {
  ...ProgrammeTeaserBox_programme
  title
  kicker
  broadcasts(first: 1) {
    edges {
      node {
        __typename
        start
        end
        id
      }
    }
  }
  id
}"""

#ALT:
"""fragment ProgrammeTableRow_programme on ProgrammeInterface {
  ...ProgrammeTeaserBox_programme
  ...LinkWithSlug_creativeWork
  title
  kicker
  id
}"""


Sfragment_ProgrammeTable_programmes = """

fragment ProgrammeTable_programmes on ProgrammeConnection {
  edges {
    node {
      __typename
      id
      ...ProgrammeTableRow_programme
    }
  }
}"""


Sfragment_ProgrammeContainer_broadcastService_fYjpM = """

fragment ProgrammeContainer_broadcastService_fYjpM on BroadcastServiceInterface {
  id
  containerToday: programmes(first: 96, orderBy: BROADCASTS_START_ASC, filter: $programmeFilter) {
    ...ProgrammeTable_programmes
  }
}"""

Sfragment_ProgrammeCalendarPage_viewer_1qA6ko = """

fragment ProgrammeCalendarPage_viewer_1qA6ko on Viewer {
  broadcastService(id: $broadcasterId) {
    __typename
    broadcastsOns {
      edges {
        node {
          __typename
          id
        }
      }
    }
    ...ProgrammeStage_broadcastService_1dgzq1
    ...ProgrammeContainer_broadcastService_1qA6ko
    id
  }
}

fragment ProgrammeStage_broadcastService_1dgzq1 on BroadcastServiceInterface {
  today: epg(dayOffset: 0) {
    current
    broadcastEvent {
      __typename
      publicationOf {
        __typename
        ...ProgrammeInfo_programme
        id
      }
      id
    }
  }
}

fragment ProgrammeContainer_broadcastService_1qA6ko on BroadcastServiceInterface {
  id
  containerToday: epg(day: $day, slots: $slots) {
    ...ProgrammeTable_programmes
  }
}

fragment ProgrammeTable_programmes on EPGEntry {
  day
  start
  current
  broadcastEvent {
    __typename
    end
    publicationOf {
      __typename
      id
      ...ProgrammeTableRow_programme
    }
    id
  }
}"""

Sfragment_SubtitlesInfo_clip = """

fragment SubtitlesInfo_clip on ClipInterface {
  hasEmbeddedSubtitles: videoFiles(first: 100, filter: {subtitles: {embedded: {eq: true}}}) {
    edges {
      node {
        __typename
        subtitles {
          edges {
            node {
              __typename
              embedded
              id
            }
          }
        }
        id
      }
    }
  }
  hasSubtitles: videoFiles(first: 100, filter: {subtitles: {timedTextFiles: {empty: {eq: false}}}}) {
    edges {
      node {
        __typename
        subtitles {
          edges {
            node {
              __typename
              timedTextFiles {
                edges {
                  node {
                    __typename
                    publicLocation
                    id
                  }
                }
              }
              id
            }
          }
        }
        id
      }
    }
  }
}"""

Sfragment_ProgrammeInfo_programme = """

fragment ProgrammeInfo_programme on ProgrammeInterface {
  id
  title
  kicker
  description
  episodeNumber
  episodeOf {
    __typename
    title
    id
  }
  ...LinkWithSlug_creativeWork
  broadcasts(first: 1) {
    edges {
      node {
        __typename
        start
        end
        id
      }
    }
  }
  ... on ClipInterface {
    ...Duration_clip
  }
}"""

Sfragment_LinkWithSlug_creativeWork = """

fragment LinkWithSlug_creativeWork on CreativeWorkInterface {
  id
  slug
}"""



Sfragment_StartPage_board_4prhdM = """

fragment StartPage_board_4prhdM on Board {
  ...Stage_board_4prhdM
}"""

#Sfragment_StartPage_board_4prhdM = """
#
#fragment StartPage_board_4prhdM on Board {
#  ...Stage_board_4prhdM
#  sections(first: 100) {
#    edges {
#      node {
#        __typename
#        ...TeaserSection_section
#        id
#      }
#    }
#  }
#}"""

#removed:
#        ...StageTeaser_section
Sfragment_Stage_board_4prhdM = """

fragment Stage_board_4prhdM on BoardInterface {
  stageTeaserSection: sections(first: 2) {
    edges {
      node {
        __typename
        ...VerticalSectionList_section
        id
      }
    }
  }
}"""

#added description, shortDescription
Sfragment_VerticalSectionList_section = """

fragment VerticalSectionList_section on SectionInterface {
  title
  verticalSectionContents: contents(first: 30) {
    edges {
      node {
        __typename
        id
        customTitle
        customKicker
        represents {
          __typename
          kicker
          title
          id
          description
          shortDescription
          ...LinkWithSlug_creativeWork
          ...Duration_clip
          ...TeaserImage_creativeWorkInterface
        }
      }
    }
  }
}"""

#cut stuff from above
"""

fragment TeaserSection_section on SectionInterface {
  title
  template {
    __typename
    id
  }
  contents(first: 10000) {
    ...StartpageSlider_teaserContentConnection
  }
}

fragment StartpageSlider_teaserContentConnection on TeaserContentConnection {
  count
  edges {
    node {
      __typename
      ...SmallTeaserContentBox_teaserContent
      ...LargeTeaserContentBox_teaserContent
      id
    }
  }
}

fragment SmallTeaserContentBox_teaserContent on TeaserContent {
  customTitle
  customKicker
  represents {
    __typename
    id
    title
    kicker
    ...LinkWithSlug_creativeWork
    ...TeaserImage_creativeWorkInterface
    ...Bookmark_clip
    ...Duration_clip
    ...Progress_clip
    ... on ProgrammeInterface {
      broadcasts(first: 1, orderBy: START_DESC) {
        edges {
          node {
            __typename
            start
            id
          }
        }
      }
    }
  }
}

fragment LargeTeaserContentBox_teaserContent on TeaserContent {
  customTitle
  customKicker
  represents {
    __typename
    id
    title
    kicker
    slug
    ...LinkWithSlug_creativeWork
    ...TeaserImage_creativeWorkInterface
    ...Bookmark_clip
    ...Duration_clip
    ...Progress_clip
  }
}

fragment TeaserImage_creativeWorkInterface on CreativeWorkInterface {
  id
  kicker
  title
  teaserImages(first: 1) {
    edges {
      node {
        __typename
        shortDescription
        id
      }
    }
  }
  defaultTeaserImage {
    __typename
    imageFiles(first: 1) {
      edges {
        node {
          __typename
          id
          publicLocation
          crops(first: 10) {
            count
            edges {
              node {
                __typename
                publicLocation
                width
                height
                id
              }
            }
          }
        }
      }
    }
    id
  }
}

fragment StageTeaser_section on SectionInterface {
  contents(first: 1) {
    edges {
      node {
        __typename
        ...StageTeaserBox_teaserContent
        id
      }
    }
  }
}

fragment StageTeaserBox_teaserContent on TeaserContent {
  customTitle
  customKicker
  represents {
    __typename
    id
    title
    kicker
    slug
    ...TeaserImage_creativeWorkInterface
    ...Duration_clip
    ...Progress_clip
    ...LinkWithSlug_creativeWork
  }
}"""

Sfragment_CategoryPage_nodes = """

fragment CategoryPage_nodes on Node {
  ... on BoardInterface {
    id
    ...ThemeBox_board
  }
}"""

Sfragment_ThemeBox_board = """

fragment ThemeBox_board on BoardInterface {
  id
  title
  uri
  description
  shortDescription
}"""

Sfragment_ThemeBox_boardALT = """

fragment ThemeBox_board on BoardInterface {
  id
  title
  uri
  sections(first: 1000) {
    count
    edges {
      node {
        __typename
        id
        contents(first: 1000) {
          count
          edges {
            node {
              __typename
              id
              represents {
                __typename
                ...TeaserImage_creativeWorkInterface
                id
              }
            }
          }
        }
      }
    }
  }
}"""



Sfragment_BoardPage_board = """

fragment BoardPage_board on Board {
  ...BoardInfo_board
  sections(first: 100) {
    edges {
      node {
        __typename
        ...TeaserSection_section
        id
      }
    }
  }
}

fragment BoardInfo_board on Board {
  title
  shortDescription
}

fragment TeaserSection_section on SectionInterface {
  title
  template {
    __typename
    id
  }
  contents(first: 10000) {
    ...StartpageSlider_teaserContentConnection
  }
}

fragment StartpageSlider_teaserContentConnection on TeaserContentConnection {
  count
  edges {
    node {
      __typename
      ...SmallTeaserContentBox_teaserContent
      ...LargeTeaserContentBox_teaserContent
      id
    }
  }
}

fragment SmallTeaserContentBox_teaserContent on TeaserContent {
  customTitle
  customKicker
  represents {
    __typename
    id
    title
    kicker
    ...LinkWithSlug_creativeWork
    ...TeaserImage_creativeWorkInterface
    ...Bookmark_clip
    ...Duration_clip
    ...Progress_clip
    ... on ProgrammeInterface {
      broadcasts(first: 1, orderBy: START_DESC) {
        edges {
          node {
            __typename
            start
            id
          }
        }
      }
    }
  }
}

fragment LargeTeaserContentBox_teaserContent on TeaserContent {
  customTitle
  customKicker
  represents {
    __typename
    id
    title
    kicker
    slug
    ...LinkWithSlug_creativeWork
    ...TeaserImage_creativeWorkInterface
    ...Bookmark_clip
    ...Duration_clip
    ...Progress_clip
  }
}

fragment LinkWithSlug_creativeWork on CreativeWorkInterface {
  id
  slug
}

fragment TeaserImage_creativeWorkInterface on CreativeWorkInterface {
  id
  kicker
  title
  teaserImages(first: 1) {
    edges {
      node {
        __typename
        shortDescription
        id
      }
    }
  }
  defaultTeaserImage {
    __typename
    imageFiles(first: 1) {
      edges {
        node {
          __typename
          id
          publicLocation
          crops(first: 10) {
            count
            edges {
              node {
                __typename
                publicLocation
                width
                height
                id
              }
            }
          }
        }
      }
    }
    id
  }
}

fragment Bookmark_clip on ClipInterface {
  id
  bookmarked
  title
}

fragment Duration_clip on ClipInterface {
  duration
}

fragment Progress_clip on ClipInterface {
  myInteractions {
    __typename
    progress
    completed
    id
  }
}
"""

#Dependencies tree
Dfragment_SubscribeAction_series 					= [Sfragment_SubscribeAction_series,					[]]
Dfragment_TeaserImage_creativeWorkInterface			= [Sfragment_TeaserImage_creativeWorkInterface,			[]]
Dfragment_TeaserListItem_node						= [Sfragment_TeaserListItem_node,						[Dfragment_TeaserImage_creativeWorkInterface]]
Dfragment_SeriesTeaserBox_node						= [Sfragment_SeriesTeaserBox_node,						[Dfragment_TeaserImage_creativeWorkInterface,Dfragment_SubscribeAction_series]]
Dfragment_SeriesIndex_viewer						= [Sfragment_SeriesIndex_viewer,						[Dfragment_SeriesTeaserBox_node,Dfragment_TeaserListItem_node]]
Dfragment_Search_viewer 							= [Sfragment_Search_viewer,								[Dfragment_SeriesIndex_viewer]]

Dfragment_Progress_clip 							= [Sfragment_Progress_clip,								[]]
Dfragment_Duration_clip 							= [Sfragment_Duration_clip,								[]]
Dfragment_Bookmark_clip 							= [Sfragment_Bookmark_clip,								[]]
Dfragment_SmallTeaserBox_node 						= [Sfragment_SmallTeaserBox_node,						[Dfragment_TeaserImage_creativeWorkInterface,Dfragment_Bookmark_clip,Dfragment_Duration_clip,Dfragment_Progress_clip]]
Dfragment_ProgrammeSlider_programmes		 		= [Sfragment_ProgrammeSlider_programmes,				[Dfragment_SmallTeaserBox_node]]
Dfragment_ChildContentRedirect_creativeWork			= [Sfragment_ChildContentRedirect_creativeWork,			[]]
Dfragment_SubscribeAction_series					= [Sfragment_SubscribeAction_series,					[]]
Dfragment_SeriesBrandBanner_series					= [Sfragment_SeriesBrandBanner_series,					[Dfragment_SubscribeAction_series]]
Dfragment_SeriesPage_viewer_2PDDaq					= [Sfragment_SeriesPage_viewer_2PDDaq,					[Dfragment_TeaserImage_creativeWorkInterface,Dfragment_SeriesBrandBanner_series,Dfragment_ChildContentRedirect_creativeWork,Dfragment_ProgrammeSlider_programmes,Dfragment_SmallTeaserBox_node]]

Dfragment_SubtitlesInfo_clip						= [Sfragment_SubtitlesInfo_clip,						[]]
Dfragment_ProgrammeTeaserBox_programme				= [Sfragment_ProgrammeTeaserBox_programme,				[Dfragment_TeaserImage_creativeWorkInterface,Dfragment_Duration_clip,Dfragment_Bookmark_clip,Dfragment_SubtitlesInfo_clip]]
Dfragment_ProgrammeTableRow_programme				= [Sfragment_ProgrammeTableRow_programme,				[Dfragment_ProgrammeTeaserBox_programme]]
Dfragment_ProgrammeTable_programmes					= [Sfragment_ProgrammeTable_programmes,					[Dfragment_ProgrammeTableRow_programme]]
Dfragment_ProgrammeContainer_broadcastService_fYjpM = [Sfragment_ProgrammeContainer_broadcastService_fYjpM, [Dfragment_ProgrammeTable_programmes]]

Dfragment_LinkWithSlug_creativeWork					= [Sfragment_LinkWithSlug_creativeWork,					[]]
Dfragment_ProgrammeInfo_programme					= [Sfragment_ProgrammeInfo_programme,					[Dfragment_LinkWithSlug_creativeWork,Dfragment_Duration_clip]]
Dfragment_ProgrammeCalendarPage_viewer_1qA6ko		= [Sfragment_ProgrammeCalendarPage_viewer_1qA6ko,		[Dfragment_ProgrammeInfo_programme,Dfragment_ProgrammeTableRow_programme]]

Dquery_SearchPageQuery								= [Squery_SearchPageQuery,								[Dfragment_Search_viewer]]
Dquery_SeriesPageRendererQuery						= [Squery_SeriesPageRendererQuery,						[Dfragment_SeriesPage_viewer_2PDDaq]]
Dquery_ProgrammeContainerRefetchQuery				= [Squery_ProgrammeContainerRefetchQuery,				[Dfragment_ProgrammeContainer_broadcastService_fYjpM]]
Dquery_ProgrammeCalendarPageRefetchQuery			= [Squery_ProgrammeCalendarPageRefetchQuery,			[Dfragment_ProgrammeCalendarPage_viewer_1qA6ko]]

Dfragment_VerticalSectionList_section				= [Sfragment_VerticalSectionList_section,				[Dfragment_LinkWithSlug_creativeWork,Dfragment_Duration_clip,Dfragment_TeaserImage_creativeWorkInterface]]
Dfragment_Stage_board_4prhdM						= [Sfragment_Stage_board_4prhdM,						[Dfragment_VerticalSectionList_section]]
Dfragment_StartPage_board_4prhdM					= [Sfragment_StartPage_board_4prhdM,					[Dfragment_Stage_board_4prhdM]]
Dquery_StartPageQuery								= [Squery_StartPageQuery,								[Dfragment_StartPage_board_4prhdM]]

Dfragment_ThemeBox_board							= [Sfragment_ThemeBox_board,							[]]
Dfragment_CategoryPage_nodes						= [Sfragment_CategoryPage_nodes,						[Dfragment_ThemeBox_board]]
Dquery_CategoryPageRendererQuery					= [Squery_CategoryPageRendererQuery,					[Dfragment_CategoryPage_nodes]]

Dfragment_BoardPage_board							= [Sfragment_BoardPage_board,							[]]
Dquery_BoardPageRendererQuery						= [Squery_BoardPageRendererQuery,						[Dfragment_BoardPage_board]]
