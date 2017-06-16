# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json
import logging
import re
import string

from django.db import models

_log = logging.getLogger(__name__)
BUILDINGSYNC_MEASURES = [
    {
        "name": "RetrofitWithCFLs",
        "display_name": "Retrofit with CFLs",
        "category": "LightingImprovements",
        "category_name": "Lighting Improvements",
    }
]


def _snake_case(display_name):
    """
    Convert the BuildingSync measure display names into reasonable snake_case for storing into
    database.

    :param display_name: BuidingSync measure displayname
    :return: string
    """
    str_re = re.compile('[{0}]'.format(re.escape(string.punctuation)))
    str = str_re.sub(' ', display_name)
    str = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', str)
    str = re.sub('([a-z0-9])([A-Z])', r'\1_\2', str).lower()
    return re.sub(' +', '_', str)


class Measure(models.Model):
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    category_display_name = models.CharField(max_length=255)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'Measure - %s.%s' % (self.category, self.name)

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'
        unique_together = ('category', 'name')

    @classmethod
    def populate_measures(cls):
        """
        Populate the list of measures from the BuildingSync
        :return:
        """
        filename = "seed/lib/buildingsync/enumerations.json"
        with open(filename) as f:
            data = json.load(f)

            for datum in data:
                # "name": "MeasureName",
                # "sub_name": "AdvancedMeteringSystems",
                # "documentation": "Advanced Metering Systems",
                # "enumerations": [
                #                     "Install advanced metering systems",
                #                     "Clean and/or repair",
                #                     "Implement training and/or documentation",
                #                     "Upgrade operating protocols, calibration, and/or sequencing",
                #                     "Other"
                #                 ],
                if datum["name"] == "MeasureName":
                    for enum in datum["enumerations"]:
                        Measure.objects.get_or_create(
                            category=_snake_case(datum["sub_name"]),
                            category_display_name=datum["documentation"],
                            name=_snake_case(enum),
                            display_name=enum,
                        )

    @classmethod
    def validate_measures(cls, data):
        """
        Take a list of measure ids or measure names and return just a list of ids.

        :param data: list, either category.name of measure or primary key
        :return: list of integers, the list are primary key of measures
        """
        if len(data) > 0:
            resp = []
            for d in data:
                try:
                    if isinstance(d, int) or d.isdigit():
                        # validate that the measure exists
                        resp.append(Measure.objects.get(pk=d).pk)
                    elif len(d) == 0:
                        continue
                    else:
                        if "." not in d or len(d) == 1:
                            _log.error("Invalid measure name: {}".format(d))
                            continue

                        measure = d.split(".")
                        resp.append(Measure.objects.get(category=measure[0], name=measure[1]).pk)
                except Measure.DoesNotExist:
                    _log.error("Could not find measure for {}".format(d))
            return resp
        else:
            return []
