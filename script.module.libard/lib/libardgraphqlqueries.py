# -*- coding: utf-8 -*-

queryDefaultPage = """query result($client: ID!, $name: ID!) {
  defaultPage(name: $name, client: $client) {
    widgets {
      title
      type
      id
    }
  }
}
"""

queryShows = """query result($client: ID!){
  showsPage(client: $client) {
    glossary {
      shows09 {
        ...f_teaser
      }
      showsA {
        ...f_teaser
      }
      showsB {
        ...f_teaser
      }
      showsC {
        ...f_teaser
      }
      showsD {
        ...f_teaser
      }
      showsE {
        ...f_teaser
      }
      showsF {
        ...f_teaser
      }
      showsG {
        ...f_teaser
      }
      showsH {
        ...f_teaser
      }
      showsI {
        ...f_teaser
      }
      showsJ {
        ...f_teaser
      }
      showsK {
        ...f_teaser
      }
      showsL {
        ...f_teaser
      }
      showsM {
        ...f_teaser
      }
      showsN {
        ...f_teaser
      }
      showsO {
        ...f_teaser
      }
      showsP {
        ...f_teaser
      }
      showsQ {
        ...f_teaser
      }
      showsR {
        ...f_teaser
      }
      showsS {
        ...f_teaser
      }
      showsT {
        ...f_teaser
      }
      showsU {
        ...f_teaser
      }
      showsV {
        ...f_teaser
      }
      showsW {
        ...f_teaser
      }
      showsX {
        ...f_teaser
      }
      showsY {
        ...f_teaser
      }
      showsZ {
        ...f_teaser
      }
    }
  }
}"""

queryShow = """query result($client: ID!, $showId: ID!){
  showPage(client: $client, showId: $showId) {
    image {
      src
    }
    teasers {
      ...f_teaser
    }
  }
}"""

queryVideo = """query result($client: ID!, $clipId: ID!, $deviceType: String) {
  playerPage (client: $client, clipId: $clipId, deviceType: $deviceType) {
    mediaCollection {
      _subtitleUrl
      _mediaArray {
        _mediaStreamArray {
          _stream
          _quality
        }
      }
    }
  }
}"""

queryWidgets = """query result($client: ID!, $widgetId: ID!) {
  widget(client: $client, widgetId: $widgetId) {
    id
    title
    teasers {
      ...f_teaser
    }
    pagination {
      totalElements
      pageSize
      pageNumber
    }
  }
}"""

queryMorePage = """query result($client: ID!, $compilationId: ID!) {
  morePage(client: $client, compilationId: $compilationId) {
    widget {
      teasers {
        ...f_teaser
      }
    }
  }
}
"""

queryProgramPage = """query result($client: ID!, $startDate: String!) {
  programPage(client: $client, startDate: $startDate) {
    widgets {
      teasers {
        ...f_teaser
      }
    }
  }
}"""

querySearchPageVOD = """query result($client: ID!, $text: String!) {
  searchPage(client: $client, text: $text) {
    vodResults {
      ...f_teaser
    }
  }
}"""

querySearchPageShow = """query result($client: ID!, $text: String!) {
  searchPage(client: $client, text: $text) {
    showResults {
      ...f_teaser
    }
  }
}"""

queryChannels = """query {
  channels {
    title
    channelKey
  }
}"""

fragmentTeaser = """

fragment f_teaser on Teaser {
  id
  links {
    target {
      id
    }
  }
  shortTitle
  mediumTitle
  longTitle
  duration
  broadcastedOn
  subtitled
  type
  images {
    ...f_images
  }
}"""

fragmentTeaserImages = """

fragment f_images on TeaserImages {
  aspect16x9 {
    src
  }
  aspect3x4 {
    src
  }
}"""