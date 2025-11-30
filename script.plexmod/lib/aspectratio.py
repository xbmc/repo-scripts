# coding=utf-8

V_AR_RATIO = None


def v_ar_ratio(w, h):
    """
    get the vertical aspect ratio difference of w/h compared to our default resolution, 16:9/1920:1080
    """
    global V_AR_RATIO
    hratio = 1080 / float(1920)
    hratio2 = h / float(w)
    V_AR_RATIO = hratio / hratio2
    return V_AR_RATIO
