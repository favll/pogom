import datetime
import pycurl
from io import BytesIO
from collections import deque

import time


class ParallelCurl:
    _num_connections = 0
    _queue_max_length = 0

    _queue = deque()
    _handles = []
    _free_handles = []

    _start_time = None
    _sampling_interval = 60
    _request_stats = {}

    num_reqs = 0
    """ Total number of requests that were queued in this class."""
    num_reqs_processed = 0
    """ Total number of finished requests."""

    # def __init__(self, num_connections: int = 35, default_options=Optional[dict]) -> None:
    def __init__(self, default_options, num_connections=2):
        """
        :param int num_connections: The number of simultaneous opened connections.
        :param dict default_options: A dictionary of pycurl options (in the format ``{pycurl.OPTION: value, ...}`` that
            will be applied to every request. Keys must be Curl-Options, as are supplied to the
            :meth:`pycurl.Curl.setopt` function, and the corresponding values must be valid parameters for the
            respective Option.

            The options that are set here and those that are set with every individual request must be exclusive. If
            one of the :py:obj:`default_options` is overwritten in an individual request, undefined behaviour occurs.

            This function can be used to set sensible defaults, such as User-Agent, Timeouts, Proxies, SSL Options and
            Redirect Policy.

            See http://curl.haxx.se/libcurl/c/curl_easy_setopt.html for an exhaustive list of available options.

            See http://pycurl.sourceforge.net/doc/curlobject.html for some information on how to use these options.
        """
        self._total_size_up = 0
        self._total_size_dl = 0
        self._num_connections = num_connections
        self._queue_max_length = self._num_connections
        self.sample_rps = 0

        if default_options is None:
            default_options = dict()

        self.m = pycurl.CurlMulti()
        # self.m.setopt(pycurl.M_PIPELINING, 1)
        # self.m.setopt(pycurl.M_MAX_TOTAL_CONNECTIONS, 30)

        for i in range(self._num_connections):
            c = pycurl.Curl()

            for key, value in default_options.items():
                c.setopt(key, value)

            self._handles.append(c)

        self._free_handles = self._handles[:]

    def add_request(self, options, success_callback, error_callback, bundle):
        """Add a request to the queue. This function will return immediately if less than the max number of requests
        are pending. Otherwise, it will be blocking until there's a free slot in the queue.

            def add_request(self,
                    options: dict,
                    success_callback: Callable[
                        [pycurl.Curl, dict, Optional[object], Optional[BytesIO], Optional[BytesIO]], None],
                    error_callback: Callable[[pycurl.Curl, dict, Optional[object], int, str], None],
                    bundle=Optional[object]) -> None:

        Sample Usage::

            pc = ParallelCurl()
            pc.add_request(on_success, on_error, {pycurl.URL: 'www.google.com'}, None)
            pc.finish_requests()

        :param dict options: Pycurl options that will be applied to this request. Keys must be Curl-Options, as are
            supplied to the :meth:`pycurl.Curl.setopt` function, and the corresponding values must be valid parameters
            for the respective Option.
            See http://curl.haxx.se/libcurl/c/curl_easy_setopt.html for a complete list of available options.

            Use the options :py:data:`pycurl.HEADERFUNCTION` and/or :py:data:`pycurl.WRITEDATA` to manually read from
            the request. If you do this, you are responsible for correctly closing the Streams. Otherwise a `io.BytesIO`
            is used to read from the stream, these objects are returned in the callback function. Closing these will
            be done automatically.

            Must not overwrite any of the default options that are set in the constructor. You are responsible for
            complying with this rule, if this is violated, behaviour is undefined.

        :param Callable success_callback: Will be called with the following parameters after the request was
            successfully executed.
            Note: If the server returned an error status code (400 or higher), this callback will be called.
            This behaviour can be altered by setting :py:data:`pycurl.FAILONERROR` to 1.

            :handle: The :py:class:`pycurl.Curl`-Handle that was used to execute this request. Can be used to extract
                information about the request. E.g. with: ``handle.getinfo(pycurl.EFFECTIVE_URL)``
            :options: The options dictionary that was used to create this request.
            :bundle: The bundle object that was passed to :meth:`add_request`.
            :header_buf: A buffer of type :py:class:`io.BytesIO` that contains the header data of the response.
                Will be closed automatically. Will be :py:obj:`None` if an own method to read the header was set using
                :py:data:`pycurl.HEADERFUNCTION` in :py:obj:`options`.
            :data_buf: A buffer of type :py:class:`io.BytesIO` that contains the content of the response.
                Will be closed automatically. Will be :py:obj:`None` if an own method to read the header was set using
                :py:data:`pycurl.WRITEDATA` in :py:obj:`options`.

        :param Callable error_callback: Will be called with the following parameters if an error was encountered.

            :handle: The :py:class:`pycurl.Curl`-Handle that was used to execute this request. Can be used to extract
                information about the request. E.g. with: ``handle.getinfo(pycurl.EFFECTIVE_URL)``
            :options: The options dictionary that was used to create this request.
            :bundle: The bundle object that was passed to :meth:`add_request`.
            :errno: The error code, see http://curl.haxx.se/libcurl/c/libcurl-errors.html for an exhaustive listing.
            :errmsg: A human readable error message.

        :param object bundle: Any object. Will not be touched and is passed through to the callback functions.
        """
        while len(self._queue) >= self._queue_max_length:
            self._download_loop()

        self.num_reqs += 1
        self._queue.append({'success_callback': success_callback, 'error_callback': error_callback,
                            'options': options, 'bundle': bundle})

    def finish_requests(self, max_time=None):
        """ Call this function to process all outstanding requests. Must be called before your script terminates. """
        if max_time:
            t = time.time()
            while self.num_reqs > self.num_reqs_processed and (time.time() - t) < max_time:
                self._download_loop()
        else:
            while self.num_reqs > self.num_reqs_processed:
                self._download_loop()



    def close(self):
        """ Closes all sockets """
        for c in self._handles:
            c.close()
        self.m.close()

    def __del__(self):
        self.close()

    def _download_loop(self):
        while self._queue and self._free_handles:
            curl = self._free_handles.pop()
            item = self._queue.popleft()

            self._prepare_handle(curl, item)
            self.m.add_handle(curl)

            if not self._start_time:
                self._start_time = time.time()

        while 1:
            if self.m.perform()[0] != pycurl.E_CALL_MULTI_PERFORM:
                break

        while 1:
            num_queued, ok_list, err_list = self.m.info_read()

            for handle in ok_list:
                self._process_ok_handle(handle)

            for handle, errno, errmsg in err_list:
                self._process_error_handle(handle, errno, errmsg)

            if num_queued == 0:
                break

        self.m.select(max(self.m.timeout() / 1000, 0))

    @staticmethod
    def _prepare_handle(curl, item):
        curl.info = item

        if pycurl.HEADERFUNCTION not in curl.info['options']:
            curl.info['header_buf'] = BytesIO()
            curl.info['options'][pycurl.HEADERFUNCTION] = curl.info['header_buf'].write
        if pycurl.WRITEDATA not in curl.info['options']:
            curl.info['data_buf'] = BytesIO()
            curl.info['options'][pycurl.WRITEDATA] = curl.info['data_buf']

        for key, value in curl.info['options'].items():
            curl.setopt(key, value)

        return curl

    def _process_ok_handle(self, handle):
        hbuf = handle.info.get('header_buf')
        dbuf = handle.info.get('data_buf')

        handle.info['success_callback'](handle, handle.info['options'], handle.info['bundle'], hbuf, dbuf)

        self._cleanup_handle(handle)

    def _process_error_handle(self, handle, errno, errmsg):
        handle.info['error_callback'](handle, handle.info['options'], handle.info['bundle'], errno, errmsg)

        self._cleanup_handle(handle)

    def _cleanup_handle(self, handle):
        if handle.info.get('header_buf'):
            handle.info.get('header_buf').close()
        if handle.info.get('data_buf'):
            handle.info.get('data_buf').close()
        handle.info = None

        self._stats(handle)

        self.m.remove_handle(handle)
        self._free_handles.append(handle)

    def _stats(self, handle):
        self.num_reqs_processed += 1

        size_up = handle.getinfo(pycurl.SIZE_UPLOAD) + handle.getinfo(pycurl.REQUEST_SIZE)
        size_dl = handle.getinfo(pycurl.SIZE_DOWNLOAD) + handle.getinfo(pycurl.HEADER_SIZE)
        self._total_size_dl += size_dl
        self._total_size_up += size_up

        total_req_time = handle.getinfo(pycurl.TOTAL_TIME)

        now = time.time()
        request_start_time = now - total_req_time
        self._request_stats[now] = (request_start_time, now, size_up, size_dl)

    def stats(self):
        if not self._start_time or not self._request_stats:
            return

        now = time.time()
        total_time = now - self._start_time

        total_rps = len(self._request_stats) / total_time
        total_speed_up = self._total_size_up / total_time
        total_speed_dl = self._total_size_dl / total_time
        av_req_time = sum((v[1] - v[0] for _, v in self._request_stats.items())) / len(self._request_stats)

        output_compact = "{total_req:>5} reqs in {total_time_m:02.0f}m{total_time_s:02.0f}s  " \
                         "[{total_rps:>5.1f} reqs/s {total_speed_up}B/s (up) {total_speed_down}B/s (down)] " \
                         "{av_req_time:.2f}s av. per request"

        status = output_compact.format(
                total_req=len(self._request_stats), total_time_m=total_time // 60, total_time_s=total_time % 60,
                total_rps=total_rps, total_speed_up=sizeof_fmt(total_speed_up),
                total_speed_down=sizeof_fmt(total_speed_dl), av_req_time=av_req_time)

        return status

    def reset_stats(self):
        self._request_stats = {}
        self._start_time = None
        self._total_size_up = 0
        self._total_size_dl = 0


def sizeof_fmt(num):
    for unit in [' ', 'K', 'M', 'G', 'T']:
        if abs(num) < 1024.0:
            return "%5.1f%s" % (num, unit)
        num /= 1024.0
    return "%.1f%s" % (num, 'Yi')
