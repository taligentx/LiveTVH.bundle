# LiveTVH - Live TV streaming for Plex via Tvheadend
# https://github.com/taligentx/LiveTVH

import base64
import time
import re

# Preferences
#
# Display the EPG zap2it ID for a show in the channel summary if the ID on theTVDB.com does not match
# due to a missing ID, outdated ID, or incorrect show match.  If the show matches correctly, consider
# contributing by updating the entry on thetvdb.com to improve search results.
# This has no effect if the EPG data does not use zap2it IDs.
improveTheTVDB = True

# Cache times
channelDataCacheTime = 60
epgCacheTime = 4200
imageCacheTime = CACHE_1MONTH
tvdbRetryInterval = CACHE_1MONTH

# /Preferences

liveTVHVersion = '1.3dev'
TITLE = 'LiveTVH'
PREFIX = '/video/livetvh'
THUMB = 'icon-default.png'
ART = 'art-default.jpg'
tvhHeaders = None
tvhAddress = None
tvhReachable = False
tvdbToken = None
tmdbBaseURL = None
tmdbGenreData = None

debug = True

def Start():
    Log.Info('LiveTVH version: ' + liveTVHVersion)
    setPrefs()


@route(PREFIX + '/validateprefs')
def ValidatePrefs():
    setPrefs()
    return True


# Setup authorization and configuration data
@route(PREFIX + '/setprefs')
def setPrefs():
    global tvhHeaders
    global tvhAddress
    global tvhReachable
    global tvdbToken
    global tmdbBaseURL
    global tmdbGenreData

    # Set Tvheadend authorization and verify connectivity to Tvheadend
    tvhAuth = base64.b64encode('%s:%s' % (Prefs['tvhUser'], Prefs['tvhPass']))
    tvhHeaders = {'Authorization': 'Basic %s' % tvhAuth}
    tvhAddress = Prefs['tvhAddress'].rstrip('/')
    tvhServerInfoURL = '%s/api/serverinfo' % tvhAddress

    try:
        tvhInfoData = JSON.ObjectFromURL(url=tvhServerInfoURL, headers=tvhHeaders, values=None, cacheTime=1)
        Log.Info('Tvheadend version: ' + tvhInfoData['sw_version'])

        if tvhInfoData['api_version'] >= 15:
            tvhReachable = True
        else:
            Log.Critical('Tvheadend version ' + tvhInfoData['sw_version'] + ' is unsupported.')
            return

    except Exception as e:
        Log.Critical('Error accessing Tvheadend: ' + str(e))
        tvhReachable = False
        return

    # Renew theTVDB authorization token if necessary
    if Prefs['prefMetadata'] and tvdbToken:
        tvdbToken = None
        tvdbAuth()

    # Retrieve themovieDB base URL for images and genre list
    if Prefs['prefMetadata']:
        tmdbConfigURL = 'https://api.themoviedb.org/3/configuration?api_key=0fd2136e80c47d0e371ee1af87eaedde'
        tmdbGenreURL = 'https://api.themoviedb.org/3/genre/movie/list?api_key=0fd2136e80c47d0e371ee1af87eaedde'

        try:
            tmdbConfigData = JSON.ObjectFromURL(url=tmdbConfigURL, values=None, cacheTime=1)
            tmdbGenreData = JSON.ObjectFromURL(url=tmdbGenreURL, values=None, cacheTime=1)
            tmdbBaseURL = tmdbConfigData['images']['base_url']

        except Exception as e:
            Log.Warn('Error accessing themovieDB: ' + str(e))


# Build the main menu
@handler(PREFIX, TITLE)
def MainMenu():
    
    if debug:
        Log.Debug('Client: ' + Client.Product)
        Log.Debug('Platform: ' + Client.Platform)
        Log.Debug('OS: ' + Platform.OS + ' ' + Platform.CPU)

    # Request channel data from Tvheadend
    tvhChannelsData = None
    tvhChannelsURL = '%s/api/channel/grid?start=0&limit=100000' % tvhAddress

    if tvhReachable:
        try:
            tvhChannelsData = JSON.ObjectFromURL(url=tvhChannelsURL, headers=tvhHeaders, values=None, cacheTime=channelDataCacheTime)
        except Exception as e:
            Log.Critical('Error retrieving Tvheadend channel data: ' + str(e))

    # Display an error message to clients if Tvheadend is malfunctional
    if tvhChannelsData is None:
        errorContainer = ObjectContainer(title1=TITLE, no_cache=True)
        errorContainer.add(DirectoryObject(title=L('channelsUnavailable')))
        return errorContainer

    # Request and set channel tags from Tvheadend
    # Tags are used as a manual method to identify codecs and stream types (video/audio or audio-only) for each channel
    tvhTagsData = None
    tvhTagsURL = '%s/api/channeltag/grid?start=0&limit=100000' % tvhAddress

    try:
        tvhTagsData = JSON.ObjectFromURL(url=tvhTagsURL, headers=tvhHeaders, values=None, cacheTime=channelDataCacheTime)
        if debug: Log.Debug('tvhTagsData: ' + str(tvhTagsData))
    except Exception as e:
        Log.Warn('Error retrieving Tvheadend channel tags data: ' + str(e))

    tvhVideoTags = {}
    tvhAudioTags = {}
    tvhStreamTypeTags = {}
    try:
        if tvhTagsData:
            for tvhTagEntry in tvhTagsData['entries']:

                # Set video tags
                if 'h264' in tvhTagEntry['name'].lower():
                    tvhVideoTags.setdefault('h264', []).append(tvhTagEntry['uuid'])

                elif 'mpeg2' in tvhTagEntry['name'].lower():
                    tvhVideoTags.setdefault('mpeg2video', []).append(tvhTagEntry['uuid'])

                # Set audio tags
                if 'aac' in tvhTagEntry['name'].lower():
                    tvhAudioTags.setdefault('aac', []).append(tvhTagEntry['uuid'])

                elif 'ac3' in tvhTagEntry['name'].lower():
                    tvhAudioTags.setdefault('ac3', []).append(tvhTagEntry['uuid'])

                elif 'mp2' in tvhTagEntry['name'].lower():
                    tvhAudioTags.setdefault('mp2', []).append(tvhTagEntry['uuid'])

                elif 'mp3' in tvhTagEntry['name'].lower():
                    tvhAudioTags.setdefault('mp3', []).append(tvhTagEntry['uuid'])

                # Set stream type tags
                if 'radio' in tvhTagEntry['name'].lower():
                    tvhStreamTypeTags.setdefault('radio', []).append(tvhTagEntry['uuid'])

    except Exception as e:
        Log.Warn('Error parsing Tvheadend channel tags data: ' + str(e))

    # Request recordings from Tvheadend
    tvhRecordingsData = None
    tvhRecordingsURL = '%s/api/dvr/entry/grid_finished' % tvhAddress

    try:
        tvhRecordingsData = JSON.ObjectFromURL(url=tvhRecordingsURL, headers=tvhHeaders, values=None, cacheTime=channelDataCacheTime)
        if int(tvhRecordingsData['total']) == 0:
            tvhRecordingsData = None

    except Exception as e:
        Log.Warn('Error retrieving Tvheadend recordings data: ' + str(e))

    # Set the number of EPG items to retrieve
    tvhEPGData = None
    try:
        if int(Prefs['prefEPGCount']) == 0:
            epgLimit = int(tvhChannelsData['total']) * 4
        else:
            epgLimit = int(tvhChannelsData['total']) * int(Prefs['prefEPGCount']) * 4

        if epgLimit > 20000: epgLimit = 20000

    except Exception as e:
        Log.Warn('Error calculating the EPG limit: ' + str(e))
        epgLimit = 20000

    # Request EPG data as UTF-8 with fallback to ISO-8859-1
    epgLoopLimit = epgLimit
    epgUTF8Encoding = True

    while True:
        try:
            tvhEPGURL = '%s/api/epg/events/grid?start=0&limit=%s' % (tvhAddress,epgLoopLimit)

            if epgUTF8Encoding:
                epgEncoding = 'utf-8'
            else:
                epgEncoding = 'latin-1'

            rawEPGData = HTTP.Request(url=tvhEPGURL, headers=tvhHeaders, cacheTime=epgCacheTime, encoding=epgEncoding, values=None).content
            rawEPGData = re.sub(r'[\x00-\x1f]', '', rawEPGData) # Strip control characters from EPG data (yep, this has actually happened)
            tvhEPGData = JSON.ObjectFromString(rawEPGData, encoding='utf-8', max_size=20971520)
            if tvhEPGData: break

        except Exception as e:
            if 'Data of size' in str(e):
                epgLoopLimit = epgLoopLimit - 1000
                if epgLoopLimit > 0:
                    Log.Warn('Tvheadend EPG data exceeded the data size limit, reducing the request: ' + str(e))
                else:
                    Log.Warn('Unable to retrieve Tvheadend EPG data within the data size limit.')
                    break

            else:
                if epgUTF8Encoding:
                    Log.Warn('Unable to retrieve Tvheadend EPG data as UTF-8, falling back to ISO-8859-1: ' + str(e))
                    epgUTF8Encoding = False
                else:
                    Log.Warn('Error retrieving Tvheadend EPG data: ' + str(e))
                    break

    # Build the channel list
    startCount = 0

    @route(PREFIX + '/channels', startCount=int)
    def channels(startCount=0, art=ART):
        pageContainer = ObjectContainer(title1=TITLE, no_cache=True)
        nextStartCount = startCount + int(Prefs['prefPageCount'])

        if tvhChannelsData:

            # Set metadata for each channel and add to the main menu
            for tvhChannel in sorted(tvhChannelsData['entries'], key=lambda t: float(t['number']))[startCount:nextStartCount]:

                # Set channel metadata using Tvheadend channel info
                try:
                    title = tvhChannel['name']
                except:
                    title = None

                if Prefs['prefChannelNumbers']:
                    if title:
                        title = str(tvhChannel['number']) + ' ' + title
                    else:
                        title = str(tvhChannel['number'])

                uuid = tvhChannel['uuid']
                streamURL = '/stream/channel/%s' % uuid
                streamVideo = None
                streamAudio = None
                streamType = None
                thumb = None
                fallbackThumb = None
                epgThumb = None
                art = R(ART)
                summary = None
                tagline = None
                source_title = None
                year = None
                rating = None
                content_rating = None
                genres = ' '
                artist = None

                # Set channel attributes using Tvheadend channel tags
                if tvhVideoTags or tvhAudioTags or tvhStreamStreamTypeTags:
                    try:
                        for tvhChannelTagEntry in tvhChannel['tags']:

                            for tvhVideoTag, tvhVideoTagUUID in tvhVideoTags.items():
                                if tvhChannelTagEntry in tvhVideoTagUUID:
                                    streamVideo = tvhVideoTag

                            for tvhAudioTag, tvhAudioTagUUID in tvhAudioTags.items():
                                if tvhChannelTagEntry in tvhAudioTagUUID:
                                    streamAudio = tvhAudioTag

                            for tvhStreamTypeTag, tvhStreamTypeTagUUID in tvhStreamTypeTags.items():
                                if tvhChannelTagEntry in tvhStreamTypeTagUUID:
                                    streamType = tvhStreamTypeTag

                    except: pass

                # Set audio channel title metadata per client
                if streamType == 'radio':
                    if Client.Product == 'Plex Web':
                        artist = title
                        title = ' '
                    else:
                        title = title
                        artist = ' '

                # Set channel metadata using Tvheadend EPG info
                if tvhEPGData:
                    for tvhEPGEntry in tvhEPGData['entries']:
                        if (
                            time.time() < int(tvhEPGEntry['stop'])
                            and tvhEPGEntry['channelUuid'] == uuid
                            and time.time() >= int(tvhEPGEntry['start'])
                            and tvhEPGEntry.get('title')):

                            epgStart = int(tvhEPGEntry.get('start'))
                            epgStop = int(tvhEPGEntry.get('stop'))
                            epgSubtitle = tvhEPGEntry.get('subtitle')
                            epgSummary = tvhEPGEntry.get('summary')
                            epgDescription = tvhEPGEntry.get('description')

                            epgDupedSubtitleSummary = False
                            if epgSubtitle and epgSummary and epgSubtitle == epgSummary:
                                epgDupedSubtitleSummary = True # Some EPG providers duplicate info in these fields

                            # Set the show title
                            title = title + ': ' + tvhEPGEntry['title']

                            # Set times
                            if Prefs['pref24Time']:
                                startTime = time.strftime('%H:%M', time.localtime(epgStart))
                                stopTime = time.strftime('%H:%M', time.localtime(epgStop))
                            else:
                                startTime = time.strftime('%I:%M%p', time.localtime(epgStart)).lstrip('0').lower()
                                stopTime = time.strftime('%I:%M%p', time.localtime(epgStop)).lstrip('0').lower()

                            # Set the titles and summary per client
                            if Client.Product == 'Plex Web':
                                title = title + '                                        ' # Force Plex Web to use the Details view by padding the title
                                tagline = startTime + '-' + stopTime

                                if epgDupedSubtitleSummary:
                                    if epgDescription:
                                        tagline = tagline + ': ' + epgSubtitle
                                        summary = epgDescription + '\n'
                                    else:
                                        summary = epgSummary + '\n'
                                else:
                                    if epgSubtitle: tagline = tagline + ': ' + epgSubtitle
                                    if epgSummary: summary = epgSummary + '\n'
                                    if epgDescription: summary = epgDescription + '\n'

                            elif Client.Product == 'Plex for Roku':
                                source_title = startTime + '-' + stopTime

                                if epgDupedSubtitleSummary:
                                    if epgDescription:
                                        source_title = source_title + ': ' + epgSubtitle
                                        summary = epgDescription + '\n'
                                    else:
                                        summary = epgSummary + '\n'
                                else:
                                    if epgSubtitle: source_title = source_title + ': ' + epgSubtitle
                                    if epgSummary: summary = epgSummary + '\n'
                                    if epgDescription: summary = epgDescription + '\n'

                            elif Client.Product == 'Plex for Android':
                                source_title = startTime + '-' + stopTime
                                summary = startTime + '-' + stopTime

                                if epgDupedSubtitleSummary:
                                    if epgDescription:
                                        title = title + ' (' + epgSubtitle + ')'
                                        summary = summary + ': ' + epgDescription + '\n'
                                    else:
                                        summary = summary + ': ' + epgSummary + '\n'
                                else:
                                    if epgSubtitle: title = title + ' (' + epgSubtitle + ')'
                                    if epgSummary or epgDescription:
                                        if epgSummary: summary = summary + ': ' + epgSummary + '\n'
                                        if epgDescription: summary = summary + ': ' + epgDescription + '\n'
                                    else:
                                        summary = summary + '\n'

                            else:
                                summary = startTime + '-' + stopTime

                                if epgDupedSubtitleSummary:
                                    if epgDescription:
                                        title = title + ' (' + epgSubtitle + ')'
                                        summary = summary + ': ' + epgDescription + '\n'
                                    else:
                                        summary = summary + ': ' + epgSummary + '\n'
                                else:
                                    if epgSubtitle: title = title + ' (' + epgSubtitle + ')'
                                    if epgSummary or epgDescription:
                                        if epgSummary: summary = summary + ': ' + epgSummary + '\n'
                                        if epgDescription: summary = summary + ': ' + epgDescription + '\n'
                                    else:
                                        summary = summary + '\n'

                            # List upcoming titles on this channel in the summary by searching for shows
                            # in the next number of hours or number of entries, whichever is greater
                            if tvhEPGEntry.get('nextEventId'):
                                nextEventID = tvhEPGEntry['nextEventId']
                                epgCount = int(Prefs['prefEPGCount'])
                                timeLimit = int(time.time()) + (int(Prefs['prefEPGCount'])*3600)
                                nextEPGCount = 1
                                nextEPGLoop = True
                                while nextEPGLoop:
                                    for nextEntry in tvhEPGData['entries']:
                                        nextEntryStart = int(nextEntry['start'])
                                        try:
                                            if nextEntry['eventId'] == nextEventID and (nextEntryStart <= timeLimit or nextEPGCount <= epgCount):
                                                if Prefs['pref24Time']:
                                                    nextStartTime = time.strftime('%H:%M', time.localtime(nextEntryStart))
                                                else:
                                                    nextStartTime = time.strftime('%I:%M%p', time.localtime(nextEntryStart)).lstrip('0').lower()

                                                if summary:
                                                    summary = summary + nextStartTime + ': ' + nextEntry['title'] + '\n'
                                                else:
                                                    summary = nextStartTime + ': ' + nextEntry['title'] + '\n'

                                                nextEventID = nextEntry['nextEventId']
                                                nextEPGCount += 1
                                                if nextEPGCount > epgCount and nextEntryStart > timeLimit:
                                                    break

                                            else:
                                                nextEPGLoop = False

                                        except KeyError: pass

                            # Check if this title has a zap2it ID
                            zap2itID = None
                            try:
                                if tvhEPGEntry.get('episodeUri'):
                                    epgID=tvhEPGEntry['episodeUri'].split('/')[3].split('.')[0]
                                    if epgID.startswith('MV') or epgID.startswith('EP') or epgID.startswith('SH'):
                                        zap2itID = epgID
                            except: pass

                            # Find metadata for this title
                            if Prefs['prefMetadata']:
                                metadataResults = metadata(title=tvhEPGEntry['title'], zap2itID=zap2itID)
                                if metadataResults['thumb']: thumb = metadataResults['thumb']
                                if metadataResults['art']: art = metadataResults['art']
                                if metadataResults['year']: year = int(metadataResults['year'])
                                if metadataResults['rating']: rating = float(metadataResults['rating'])
                                if metadataResults['content_rating']: content_rating = metadataResults['content_rating']
                                if metadataResults['genres']: genres = metadataResults['genres']
                                if metadataResults['zap2itMissingID'] and improveTheTVDB:
                                    summary = metadataResults['zap2itMissingID'] + ' | ' + summary

                            # Check the EPG entry for a thumbnail
                            if tvhEPGEntry.get('image') and tvhEPGEntry['image'].startswith('http'):
                                epgThumb = tvhEPGEntry['image']

                # Use EPG thumbnails from Tvheadend if a thumbnail is not available from the metadata providers
                if thumb is None and epgThumb:
                    thumb = epgThumb

                if fallbackThumb is None and epgThumb:
                    fallbackThumb = epgThumb

                # Use channel icons from Tvheadend if no other thumbnail is available
                try:
                    if thumb is None:
                        if tvhChannel['icon_public_url'].startswith('imagecache'):
                            thumb = '%s/%s' % (tvhAddress, tvhChannel['icon_public_url'])
                        elif tvhChannel['icon_public_url'].startswith('http'):
                            thumb = tvhChannel['icon_public_url']

                    if tvhChannel['icon_public_url'].startswith('imagecache'):
                        fallbackThumb = '%s/%s' % (tvhAddress, tvhChannel['icon_public_url'])
                    elif tvhChannel['icon_public_url'].startswith('http'):
                        fallbackThumb = tvhChannel['icon_public_url']

                except: pass

                # Set the channel object type - this determines if thumbnails are displayed as posters or video clips
                # Plex for Roku only displays source_title for VideoClipObjects
                if streamType == 'radio':
                    channelType = 'TrackObject'
                else:
                    if Client.Product == 'Plex Home Theater':
                        channelType = 'MovieObject'
                    elif Client.Product == 'Plex for Roku' or not Prefs['prefMetadata']:
                        channelType = 'VideoClipObject'
                    else:
                        channelType = 'MovieObject'

                # Build and add the channel to the main menu
                pageContainer.add(
                    channel(
                        channelType=channelType,
                        title=title,
                        streamURL=streamURL,
                        streamVideo=streamVideo,
                        streamAudio=streamAudio,
                        thumb=thumb,
                        fallbackThumb=fallbackThumb,
                        art=art,
                        summary=summary,
                        tagline=tagline,
                        source_title=source_title,
                        year=year,
                        rating=rating,
                        content_rating=content_rating,
                        genres=genres,
                        artist=artist))

            # Add recordings and preferences to the end of the channel list because several clients have display
            # issues when these types of objects are at the beginning of the container
            if len(tvhChannelsData['entries']) < int(Prefs['prefPageCount']):
                pageContainer.add(
                    DirectoryObject(
                        key=Callback(
                            recordings,
                            tvhVideoTags=tvhVideoTags,
                            tvhAudioTags=tvhAudioTags),
                        title=L('recordings'),
                        thumb=R('recordings.png')))

                pageContainer.add(PrefsObject(title=L('preferences')))

            # Paginate the channel list
            if len(tvhChannelsData['entries']) > nextStartCount:
                pageContainer.add(NextPageObject(key=Callback(channels, startCount=nextStartCount), title=L('next'), thumb=R('next.png')))

                # Add recordings and preferences to the end of the first page of the channel list when paginated
                if tvhRecordingsData and startCount == 0:
                    pageContainer.add(
                        DirectoryObject(
                            key=Callback(
                                recordings,
                                tvhVideoTags=tvhVideoTags,
                                tvhAudioTags=tvhAudioTags),
                            title=L('recordings'),
                            thumb=R('recordings.png')))

                    pageContainer.add(PrefsObject(title=L('preferences')))

        return pageContainer
    return channels()


# Build the channel
@route(PREFIX + '/channel', year=int, rating=float, container=bool, checkFiles=int)
def channel(
        channelType, title, streamURL, streamVideo, streamAudio, thumb, fallbackThumb, art, summary, tagline, source_title, year,
        rating, content_rating, genres, artist, container=False, checkFiles=0, **kwargs):

    if debug:
        Log('Title: ' + str(title))
        Log('Type: ' + str(channelType))
        Log('Video: ' + str(streamVideo))
        Log('Audio: ' + str(streamAudio))

    rating_key = ''.join(filter(str.isdigit, streamURL)) + str(int(time.time()))

    videoChannelMetadata = dict(
        key=Callback(
            channel, channelType=channelType, title=title, streamURL=streamURL, streamVideo=streamVideo, streamAudio=streamAudio, thumb=thumb,
            fallbackThumb=fallbackThumb, art=art, summary=summary, tagline=tagline, source_title=source_title, year=year, rating=rating,
            content_rating=content_rating, genres=genres, artist=artist, container=True, checkFiles=0, **kwargs),
        rating_key = rating_key,
        title = title,
        thumb = Callback(image, url=thumb, fallback=fallbackThumb),
        art = Callback(image, url=art, fallback=R(ART)),
        summary = summary,
        source_title = source_title,
        tagline = tagline,
        year = year,
        rating = rating,
        content_rating = content_rating,
        genres = [genres])

    audioChannelMetadata = dict(
        key=Callback(
            channel, channelType=channelType, title=title, streamURL=streamURL, streamVideo=streamVideo, streamAudio=streamAudio, thumb=thumb,
            fallbackThumb=fallbackThumb, art=art, summary=summary, tagline=tagline, source_title=source_title, year=year, rating=rating,
            content_rating=content_rating, genres=genres, artist=artist, container=True, checkFiles=0, **kwargs),
        rating_key = streamURL,
        thumb = Callback(image, url=thumb, fallback=fallbackThumb),
        art = Callback(image, url=art, fallback=R(ART)),
        title = title,
        artist = artist,
        rating = rating,
        genres = [genres])

    if streamVideo and streamAudio:
        videoChannelMediaData = dict(
        items = [
            MediaObject(
                parts = [PartObject(key=Callback(stream, streamURL=streamURL))],
                video_resolution = '1080',
                container = 'mpegts',
                bitrate = 10000,
                width = 1920,
                height = 1080,
                video_codec = streamVideo,
                audio_codec = streamAudio,
                optimized_for_streaming = True)])

    else:
        videoChannelMediaData = dict(
            items = [
                MediaObject(
                    parts = [PartObject(
                        key=Callback(stream, streamURL=streamURL))],
                    optimized_for_streaming = True)])

    if channelType == 'TrackObject':
        if streamAudio:
            audioChannelMediaData = dict(
                items = [
                    MediaObject(
                        parts = [PartObject(key=Callback(stream, streamURL=streamURL))],
                        audio_codec = streamAudio,
                        audio_channels = 2,
                        optimized_for_streaming = True)])

        else:
            audioChannelMediaData = dict(
                items = [
                    MediaObject(
                        parts = [PartObject(key=Callback(stream, streamURL=streamURL))],
                        audio_channels = 2,
                        optimized_for_streaming = True)])

    # Build channel data with the codec specified in the Tvheadend channel tag if available
    if channelType == 'TrackObject':
        channelData = audioChannelMetadata.copy()
        channelData.update(audioChannelMediaData)
        channelObject = TrackObject(**channelData)

    else:
        channelData = videoChannelMetadata.copy()
        channelData.update(videoChannelMediaData)

        # Set the framework object type
        if channelType == 'MovieObject':
            channelObject = MovieObject(**channelData)

        elif channelType == 'VideoClipObject':
            channelObject = VideoClipObject(**channelData)

    if container:
        return ObjectContainer(objects=[channelObject])
    else:
        return channelObject


# Build the Tvheadend stream URL and verify availability
@route(PREFIX + '/stream')
@indirect
def stream(streamURL):

    # Add basic authentication info to the stream URL - Plex ignores the headers parameter in PartObject
    tvhBasicAuth = '//%s:%s@' % (Prefs['tvhUser'], Prefs['tvhPass'])
    tvhAuthAddress = tvhAddress.replace('//', tvhBasicAuth)
    playbackURL = '%s%s' % (tvhAuthAddress, streamURL)

    if Prefs['tvhProfile']:
        playbackURL = playbackURL + '?profile=' + Prefs['tvhProfile']

    # Verify the channel is available before returning it to PartObject
    testURL = '%s%s' % (tvhAddress, streamURL)

    try:
        responseCode = HTTP.Request(testURL, headers=tvhHeaders, values=None, cacheTime=None, timeout=2).headers
        return IndirectResponse(MovieObject, key=playbackURL)

    except Exception as e:
        Log.Warn('Tvheadend is not responding to this channel request - verify that there are available tuners: ' + repr(e))
        raise Ex.MediaNotAvailable


# Build the Tvheadend recordings list
@route(PREFIX + '/recordings', tvhVideoTags=dict, tvhAudioTags=dict, startCount=int)
def recordings(tvhVideoTags, tvhAudioTags, startCount=0):
    nextStartCount = startCount + int(Prefs['prefPageCount'])
    recordingsContainer = ObjectContainer(title1=L('recordings'), no_cache=True)

    # Request recordings from Tvheadend
    tvhRecordingsData = None
    tvhRecordingsURL = '%s/api/dvr/entry/grid_finished' % tvhAddress

    try:
        tvhRecordingsData = JSON.ObjectFromURL(url=tvhRecordingsURL, headers=tvhHeaders, values=None, cacheTime=channelDataCacheTime)
    except Exception as e:
        Log.Warn('Error retrieving Tvheadend recordings data: ' + str(e))

    # Request channel data from Tvheadend
    tvhChannelsData = None
    tvhChannelsURL = '%s/api/channel/grid?start=0&limit=100000' % tvhAddress

    try:
        tvhChannelsData = JSON.ObjectFromURL(url=tvhChannelsURL, headers=tvhHeaders, values=None, cacheTime=channelDataCacheTime)
    except Exception as e:
        Log.Critical('Error retrieving Tvheadend channel data: ' + str(e))

    for tvhRecording in sorted(tvhRecordingsData['entries'], key=lambda r: r['start'], reverse=True)[startCount:nextStartCount]:

        title = tvhRecording['disp_title']
        streamURL = '/' + tvhRecording['url']
        streamVideo = None
        streamAudio = None
        thumb = None
        fallbackThumb = None
        art = R(ART)
        summary = None
        tagline = None
        source_title = None
        year = None
        rating = None
        content_rating = None
        genres = ' '
        artist = None

        # Set recording time for recordings today
        if time.strftime('%Y%m%d', time.localtime()) == time.strftime('%Y%m%d', time.localtime(tvhRecording['start'])):
            if Prefs['pref24Time']:
                startTime = 'Today, ' + time.strftime('%H:%M', time.localtime(tvhRecording['start']))
                stopTime = time.strftime('%H:%M', time.localtime(tvhRecording['stop']))
                recordingTime = startTime + '-' + stopTime
            else:
                startTime = 'Today, ' + time.strftime('%I:%M%p', time.localtime(tvhRecording['start'])).lstrip('0').lower()
                stopTime = time.strftime('%I:%M%p', time.localtime(tvhRecording['stop'])).lstrip('0').lower()
                recordingTime = startTime + '-' + stopTime

        # Set recording time for recordings within the past 6 days
        elif (time.time() - tvhRecording['start']) < 518400:
            if Prefs['pref24Time']:
                startTime = time.strftime('%A, %H:%M', time.localtime(tvhRecording['start']))
                stopTime = time.strftime('%H:%M', time.localtime(tvhRecording['stop']))
                recordingTime = startTime + '-' + stopTime
            else:
                startTime = time.strftime('%A, ', time.localtime(tvhRecording['start'])).lstrip('0')
                startTime = startTime + time.strftime('%I:%M%p', time.localtime(tvhRecording['start'])).lstrip('0').lower()
                stopTime = time.strftime('%I:%M%p', time.localtime(tvhRecording['stop'])).lstrip('0').lower()
                recordingTime = startTime + '-' + stopTime

        # Set recording time for recordings this year
        elif time.strftime('%Y', time.localtime()) == time.strftime('%Y', time.localtime(tvhRecording['start'])):
                recordingTime = time.strftime('%B %d', time.localtime(tvhRecording['start']))

        else:
            recordingTime = time.strftime('%B %d, %Y', time.localtime(tvhRecording['start']))

        # Set the recording codec based on the Tvheadend channel tags
        try:
            for tvhChannel in tvhChannelsData['entries']:
                if tvhChannel['uuid'] == tvhRecording['channel']:
                    for tvhChannelTagEntry in tvhChannel['tags']:

                        for tvhVideoTag, tvhVideoTagUUID in tvhVideoTags.items():
                            if tvhChannelTagEntry in tvhVideoTagUUID:
                                streamVideo = tvhVideoTag

                        for tvhAudioTag, tvhAudioTagUUID in tvhAudioTags.items():
                            if tvhChannelTagEntry in tvhAudioTagUUID:
                                streamAudio = tvhAudioTag

        except: pass

        # Set the channel object type - this determines if thumbnails are displayed as posters or video clips
        # Plex for Roku only displays source_title for VideoClipObjects
        if Client.Product == 'Plex Home Theater':
            channelType = 'MovieObject'
        elif Client.Product == 'Plex for Roku' or not Prefs['prefMetadata']:
            channelType = 'VideoClipObject'
        else:
            channelType = 'MovieObject'

        # Set the titles and summary per client
        if Client.Product == 'Plex Web':
            title = title + '                              ' # Force Plex Web to use the Details view by padding the title
            tagline = recordingTime
            if tvhRecording['disp_subtitle']:
                tagline = tagline + ': ' + tvhRecording['disp_subtitle']
            summary = tvhRecording['disp_description']

        elif Client.Product == 'Plex for Roku':
            source_title = recordingTime
            if tvhRecording['disp_subtitle']:
                source_title = source_title + ': ' + tvhRecording['disp_subtitle']
            summary = tvhRecording['disp_description']

        elif Client.Product == 'Plex for Android':
            source_title = recordingTime
            if tvhRecording['disp_subtitle']:
                title = title + ' (' + tvhRecording['disp_subtitle'] + ')'
            summary = recordingTime
            if tvhRecording['disp_description']:
                summary = summary + ': ' + tvhRecording['disp_description']

        else:
            if tvhRecording['disp_subtitle']:
                title = title + ' (' + tvhRecording['disp_subtitle'] + ')'
            summary = recordingTime
            if tvhRecording['disp_description']:
                summary = summary + ': ' + tvhRecording['disp_description']

        # Find metadata for this title
        if Prefs['prefMetadata']:
            metadataResults = metadata(title=tvhRecording['disp_title'])
            if metadataResults['thumb']: thumb = metadataResults['thumb']
            if metadataResults['art']: art = metadataResults['art']
            if metadataResults['year']: year = int(metadataResults['year'])
            if metadataResults['rating']: rating = float(metadataResults['rating'])
            if metadataResults['content_rating']: content_rating = metadataResults['content_rating']
            if metadataResults['genres']: genres = metadataResults['genres']

        # Use channel icons from Tvheadend as a fallback
        try:
            if thumb is None and tvhRecording['channel_icon'].startswith('imagecache'):
                thumb = '%s/%s' % (tvhAddress, tvhRecording['channel_icon'])

            if tvhRecording['channel_icon'].startswith('imagecache'):
                fallbackThumb ='%s/%s' % (tvhAddress, tvhRecording['channel_icon'])

        except: pass

        # Build and add the recording to the recordings menu
        recordingsContainer.add(
            channel(
                channelType=channelType,
                title=title,
                streamURL=streamURL,
                streamVideo=streamVideo,
                streamAudio=streamAudio,
                thumb=thumb,
                fallbackThumb=fallbackThumb,
                art=art,
                summary=summary,
                tagline=tagline,
                source_title=source_title,
                year=year,
                rating=rating,
                content_rating=content_rating,
                genres=genres,
                artist=artist))

    # Paginate the channel list
    if len(tvhRecordingsData['entries']) > nextStartCount:
        recordingsContainer.add(NextPageObject(
            key=Callback(
                recordings,
                tvhCodecTags=tvhCodecTags,
                startCount=nextStartCount),
            title=L('next'),
            thumb=R('next.png')))

    return recordingsContainer


# Search for images with fallback
# theTVDB API requires a separate HTTP request for each piece of artwork, so the
# channel list load time can be reduced by running the search asynchronously
@route(PREFIX + '/image')
def image(url=None, fallback=None):
    if url is None and fallback is None:
        return None

    if 'api.thetvdb.com' in url:
        tvdbHeaders = {'Authorization' : 'Bearer %s' % tvdbToken}
        tvdbImageData = None

        try:
            tvdbImageData = JSON.ObjectFromURL(url=url, headers=tvdbHeaders, values=None, cacheTime=imageCacheTime)

        except Ex.HTTPError as e:
            if e.code == 404:
                if fallback == R(ART):
                    return Redirect(R(ART))

                elif fallback:
                    if tvhAddress in fallback:
                        imageContent = HTTP.Request(url=fallback, headers=tvhHeaders, cacheTime=imageCacheTime, values=None).content
                    else:
                        imageContent = HTTP.Request(url=fallback, cacheTime=imageCacheTime, values=None).content

                    return DataObject(imageContent, 'image/jpeg')

                else: return None

        if tvdbImageData:
            for tvdbImageResult in tvdbImageData['data']:
                url = 'http://thetvdb.com/banners/' + tvdbImageResult['fileName']
                try:
                    imageContent = HTTP.Request(url, cacheTime=imageCacheTime, values=None).content
                    return DataObject(imageContent, 'image/jpeg')
                except Exception as e:
                    Log.Warn('Error retrieving image: ' + str(e))
                    return None

    elif tvhAddress in url:
        try:
            imageContent = HTTP.Request(url=url, headers=tvhHeaders, cacheTime=imageCacheTime, values=None).content
            return DataObject(imageContent, 'image/jpeg')
        except Exception as e:
            Log.Warn('Error retrieving image: ' + str(e))
            return None

    elif url == R(ART):
        return Redirect(R(ART))

    else:
        try:
            imageContent = HTTP.Request(url, cacheTime=imageCacheTime, values=None).content
            return DataObject(imageContent, 'image/jpeg')
        except Exception as e:
            Log.Warn('Error retrieving image: ' + str(e))
            return None


# Search for metadata
@route(PREFIX + '/metadata')
def metadata(title, zap2itID=None):
    thumb = None
    art = None
    year = None
    rating = None
    content_rating = None
    genres = None
    zap2itMissingID = None

    # Skip searching theTVDB if EPG data states the title is a movie
    if str(zap2itID).startswith('MV'):
        epgMovie = True
    else:
        epgMovie = False

    # Search theTVDB
    if (thumb is None or art is None) and not epgMovie:
        tvdbResults = tvdb(title, zap2itID)
        if tvdbResults:
            if thumb is None: thumb = tvdbResults['poster']
            if art is None: art = tvdbResults['fanart']
            if rating is None: rating = tvdbResults['siteRating']
            if content_rating is None: content_rating = tvdbResults['rating']
            if genres is None: genres = tvdbResults['genres']
            zap2itMissingID = tvdbResults['zap2itMissingID']

    # Search themovieDB
    if thumb is None or art is None:
        tmdbResults = tmdb(title)
        if tmdbResults:
            if thumb is None: thumb = tmdbResults['poster']
            if art is None: art = tmdbResults['backdrop']
            if rating is None: rating = tmdbResults['vote_average']
            if year is None: year = tmdbResults['year']
            if genres is None: genres = tmdbResults['genres']

    return {
        'thumb': thumb,
        'art': art,
        'year': year,
        'rating': rating,
        'content_rating': content_rating,
        'genres': genres,
        'zap2itMissingID': zap2itMissingID }


# Retrieve an authorization token from theTVDB
@route(PREFIX + '/tvdbauth')
def tvdbAuth():
    global tvdbToken

    tvdbLoginURL = 'https://api.thetvdb.com/login'
    tvdbApiKeyJSON = '{"apikey" : "C7DE76F57D6BE6CE"}'
    tvdbHeaders = {'content-type': 'application/json'}

    try:
        tvdbResponse = HTTP.Request(url=tvdbLoginURL, headers=tvdbHeaders, data=tvdbApiKeyJSON, cacheTime=1).content
        tvdbTokenData = JSON.ObjectFromString(tvdbResponse)
        tvdbToken = tvdbTokenData['token']

    except Ex.HTTPError as e:
        Log.Warn('Failed to retrieve theTVDB authorization token: ' + str(e))
        tvdbToken = False


# Search theTVDB for metadata
@route(PREFIX + '/tvdb')
def tvdb(title, zap2itID, zap2itMissingID=None):
    tvdbPosterSearchURL = None
    tvdbFanartSearchURL = None
    tvdbRating = None
    tvdbSiteRating = 0.0
    tvdbGenres = None
    tvdbID = None

    # Skip searching for this title if the theTVDB had no results within tvdbRetryInterval.
    # This uses the framework Dict as a cache because Plex does not cache the HTTP 404 response from theTVDB API.
    if title in Dict:
        if time.time() >= Dict[title]: pass
        else:
            m, s = divmod(int(Dict[title] - time.time()), 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)
            if d != 0:
                if d == 1:
                    Log.Info('theTVDB previously had no results for ' + title + ', will try again after 1 day, %sh.' % h)
                else:
                    Log.Info('theTVDB previously had no results for ' + title + ', will try again after %s days.' % d)
            elif h != 0:
                if h == 1:
                    Log.Info('theTVDB previously had no results for ' + title + ', will try again after 1 hour, %sm.' % m)
                else:
                    Log.Info('theTVDB previously had no results for ' + title + ', will try again after %s hours.' % h)
            else:
                if m == 1:
                    Log.Info('theTVDB previously had no results for ' + title + ', will try again after 1m, %ss.' % s)
                else:
                    Log.Info('theTVDB previously had no results for ' + title + ', will try again after %s minutes.' % m)
            return None

    # Request an authorization token if it doesn't exist
    if tvdbToken is None:
        Log.Info('Requesting an authorization token for theTVDB')
        tvdbAuth()
        return tvdb(title, zap2itID)

    elif not tvdbToken:
        Log.Info('theTVDB authorization failed.')
        return {'poster': tvdbPosterSearchURL, 'fanart': tvdbFanartSearchURL}

    # Search using zap2it ID if available, otherwise search by name
    tvdbHeaders = {'Authorization' : 'Bearer %s' % tvdbToken}

    if zap2itID:
        tvdbSearchURL = 'https://api.thetvdb.com/search/series?zap2itId=%s' % String.Quote(zap2itID)
    else:
        tvdbSearchURL = 'https://api.thetvdb.com/search/series?name=%s' % String.Quote(title)

    try:
        tvdbData = JSON.ObjectFromURL(url=tvdbSearchURL, headers=tvdbHeaders, values=None, cacheTime=imageCacheTime)

        for tvdbResult in tvdbData['data']:
            if zap2itID:
                tvdbID = tvdbResult['id']
                break

            elif String.LevenshteinDistance(tvdbResult['seriesName'], title) == 0:
                tvdbID = tvdbResult['id']
                if zap2itMissingID:
                    Log.Info('Found ' + title + ' at http://thetvdb.com/?tab=series&id=' + str(tvdbID)
                            + ' by name but not by zap2it ID ' + zap2itMissingID
                            + ' - if this match is correct, consider adding the zap2it ID to theTVDB.com to improve search results.')
                break

    except Ex.HTTPError as e:
        if e.code == 401:
            Log.Info('theTVDB authorization token is invalid, requesting a new one.')
            tvdbAuth()
            return tvdb(title, zap2itID)

        if e.code == 404:
            # Search again by name if there are no results by zap2it ID, and save the ID to report
            # a possible missing/mismatched ID on thetvdb.com if there is a match by name
            if zap2itID:
                zap2itMissingID = zap2itID
                zap2itID = None
                return tvdb(title, zap2itID, zap2itMissingID)
            else:
                Dict[title] = time.time() + tvdbRetryInterval
                h, m = divmod(int(tvdbRetryInterval), 3600)
                d, h = divmod(h, 24)
                Log.Info('No results from theTVDB for ' + title + ', skipping lookup for %s days.' % d)
                return None

        else:
            Log.Warn('Error while searching theTVDB: ' + str(e))
            return None

    if tvdbID:
        tvdbPosterSearchURL = 'https://api.thetvdb.com/series/%s/images/query?keyType=poster' % tvdbID
        tvdbFanartSearchURL = 'https://api.thetvdb.com/series/%s/images/query?keyType=fanart' % tvdbID

        # Search for metadata
        tvdbMetadataSearchURL = 'https://api.thetvdb.com/series/%s' % tvdbID
        tvdbMetadata = None

        try:
            tvdbMetadata = JSON.ObjectFromURL(url=tvdbMetadataSearchURL, headers=tvdbHeaders, values=None, cacheTime=imageCacheTime)
        except Ex.HTTPError as e:
            if e.code == 404:
                Log.Info('No metadata from theTVDB for ' + title)

        if tvdbMetadata:
            if tvdbMetadata['data']['rating'] != '':
                tvdbRating = tvdbMetadata['data']['rating']
            if tvdbMetadata['data']['siteRating'] != '':
                tvdbSiteRating = tvdbMetadata['data']['siteRating']
            if tvdbMetadata['data']['genre'] != []:

                # Convert genres to a string - Plex will not accept a list directly for genre in the channel object
                tvdbGenres = str(tvdbMetadata['data']['genre']).lstrip('[').rstrip(']').replace("'", '')

    else:
        Dict[title] = time.time() + tvdbRetryInterval
        h, m = divmod(int(tvdbRetryInterval), 3600)
        d, h = divmod(h, 24)
        if d == 1:
            Log.Info('No results from theTVDB for ' + title + ', skipping lookup for 1 day, %sh.' % h)
        else:
            Log.Info('No results from theTVDB for ' + title + ', skipping lookup for %s days.' % d)

        return None

    return {
        'poster': tvdbPosterSearchURL,
        'fanart': tvdbFanartSearchURL,
        'rating': tvdbRating,
        'siteRating': tvdbSiteRating,
        'genres': tvdbGenres,
        'zap2itMissingID': zap2itMissingID}


# Search The Movie Database for metadata
@route(PREFIX + '/tmdb')
def tmdb(title):
    tmdbData = None
    tmdbPoster = None
    tmdbBackdrop = None
    tmdbYear = None
    tmdbVoteAverage = 0.0
    tmdbSearchURL = 'https://api.themoviedb.org/3/search/multi?api_key=0fd2136e80c47d0e371ee1af87eaedde&query=%s' % String.Quote(title)
    tmdbGenres = None

    # Search
    try:
        tmdbData = JSON.ObjectFromURL(url=tmdbSearchURL, cacheTime=imageCacheTime, values=None)

    except Exception as e:
        Log.Warn('Error retrieving TMDb data:  ' + str(e))

    if tmdbData is None:
        Log.Info('No results from TMDb for ' + title)

    # Check for a matching movie or TV show
    elif int(tmdbData['total_results']) > 0 :
        for tmdbResult in tmdbData['results']:
            tmdbMatchedTV = False
            tmdbMatchedMovie = False
            if tmdbResult.get('name') and String.LevenshteinDistance(tmdbResult['name'], title) == 0:
                tmdbMatchedTV = True
            elif tmdbResult.get('title') and String.LevenshteinDistance(tmdbResult['title'], title) == 0:
                tmdbMatchedMovie = True

            if (
                (tmdbMatchedTV or tmdbMatchedMovie)
                and tmdbResult['media_type'] in ['movie', 'tv']
                and (tmdbResult['poster_path'] or tmdbResult['backdrop_path'])):

                if tmdbResult['poster_path']:
                    tmdbPoster = tmdbBaseURL + 'w342' + tmdbResult['poster_path']

                if tmdbResult['backdrop_path']:
                    tmdbBackdrop = tmdbBaseURL + 'original' + tmdbResult['backdrop_path']

                if tmdbResult.get('vote_average'):
                        tmdbVoteAverage = float(tmdbResult['vote_average'])

                if tmdbMatchedMovie and tmdbResult.get('release_date'):
                    tmdbYear = int(tmdbResult['release_date'].split('-')[0])

                if tmdbResult.get('genre_ids'):
                    for genreResultID in tmdbResult['genre_ids']:
                        for genreList in tmdbGenreData['genres']:
                            if genreResultID == genreList['id']:
                                if tmdbGenres is None:
                                    tmdbGenres = genreList['name']
                                else:
                                    tmdbGenres = tmdbGenres + ', ' + genreList['name']
            break

    return {
        'poster': tmdbPoster,
        'backdrop': tmdbBackdrop,
        'year': tmdbYear,
        'vote_average': tmdbVoteAverage,
        'genres': tmdbGenres}
