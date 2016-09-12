# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.test import TestCase

from seed import models as seed_models
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    PropertyState,
    Column,
    ColumnMapping,
)


class TestColumns(TestCase):
    """Test the clean methods on BuildingSnapshotModel."""

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.fake_org = Organization.objects.create()
        OrganizationUser.objects.create(
            user=self.fake_user,
            organization=self.fake_org
        )

    def test_get_column_mapping(self):
        """Honor organizational bounds, get mapping data."""
        org1 = Organization.objects.create()
        org2 = Organization.objects.create()

        raw_column = seed_models.Column.objects.create(
            column_name=u'Some Weird City ID',
            organization=org2
        )
        mapped_column = seed_models.Column.objects.create(
            column_name=u'custom_id_1',
            organization=org2
        )
        column_mapping1 = seed_models.ColumnMapping.objects.create(
            super_organization=org2,
        )
        column_mapping1.column_raw.add(raw_column)
        column_mapping1.column_mapped.add(mapped_column)

        # Test that it Doesn't give us a mapping from another org.
        self.assertEqual(
            seed_models.get_column_mapping(raw_column, org1, 'column_mapped'),
            None
        )

        # Correct org, but incorrect destination column.
        self.assertEqual(
            seed_models.get_column_mapping('random', org2, 'column_mapped'),
            None
        )

        # Fully correct example
        self.assertEqual(
            seed_models.get_column_mapping(
                raw_column.column_name, org2, 'column_mapped'
            ),
            (u'PropertyState', u'custom_id_1', 100)
        )

    def test_get_column_mappings(self):
        """We produce appropriate data structure for mapping"""
        expected = dict(sorted([
            (u'example_9', u'mapped_9'),
            (u'example_8', u'mapped_8'),
            (u'example_7', u'mapped_7'),
            (u'example_6', u'mapped_6'),
            (u'example_5', u'mapped_5'),
            (u'example_4', u'mapped_4'),
            (u'example_3', u'mapped_3'),
            (u'example_2', u'mapped_2'),
            (u'example_1', u'mapped_1'),
            (u'example_0', u'mapped_0')
        ]))
        org = Organization.objects.create()

        raw = []
        mapped = []
        for x in range(10):
            raw.append(seed_models.Column.objects.create(
                column_name='example_{0}'.format(x), organization=org
            ))
            mapped.append(seed_models.Column.objects.create(
                column_name='mapped_{0}'.format(x), organization=org
            ))

        for x in range(10):
            column_mapping = seed_models.ColumnMapping.objects.create(
                super_organization=org,
            )

            column_mapping.column_raw.add(raw[x])
            column_mapping.column_mapped.add(mapped[x])

        test_mapping, _ = seed_models.get_column_mappings(org)
        self.assertDictEqual(test_mapping, expected)

    # def test_save_mappings(self):
    #     # Test that we can upload a mapping hash
    #     test_map = [
    #         # a: field in the db
    #         # b: field in the datafile
    #         ["eui", "my energy use intensity"],
    #         ["best lab", "hawkins"],
    #         ["concatenated", ["one", "two"]]
    #     ]
    #
    #     seed_models.Column.create_mappings(test_map, self.fake_org,
    #                                        self.fake_user)
    #
    #     test_mapping, _ = seed_models.get_column_mappings(self.fake_org)
    #
    #     expected = {
    #         u'hawkins': u'best lab',
    #         u'my energy use intensity': u'eui'
    #     }
    #     # TODO: Concatenation is broken or never worked... that is why there is only 2
    #     self.assertDictEqual(expected, test_mapping)
    #
    #     c = Column.objects.filter(column_name='hawkins')[0]
    #     self.assertEqual(c.is_extra_data, True)

    def test_save_mappings_dict(self):
        """
        Test the way of saving mappings, which is dict-based instead of list of list of list.
        """

        test_map = [
            {
                'from_field': 'eui',
                'to_field': 'site_eui',
                'to_table_name': 'PropertyState',
            },
            {
                'from_field': 'address',
                'to_field': 'address',
                'to_table_name': 'TaxLotState'
            },
            {
                'from_field': 'Wookiee',
                'to_field': 'Dothraki',
                'to_table_name': 'PropertyState',
            },
            {
                'from_field': 'Ewok',
                'to_field': 'Merovingian',
                'to_table_name': 'TaxLotState',
            },
            {
                'from_field': 'Ewok',
                'to_field': 'Hattin',
                'to_table_name': 'TaxLotState',
            },
        ]

        seed_models.Column.create_mappings(test_map, self.fake_org, self.fake_user)
        test_mapping, _ = seed_models.get_column_mappings(self.fake_org)
        expected = {
            u'Wookiee': u'Dothraki',
            u'address': u'address',
            u'eui': u'site_eui',
            # u'Ewok': u'Merovingian',
            u'Ewok': u'Hattin',
        }
        self.assertDictEqual(expected, test_mapping)
        self.assertTrue(test_mapping['Ewok'], 'Hattin')

        c_wookiee = Column.objects.filter(column_name='Wookiee')[0]
        self.assertEqual(c_wookiee.is_extra_data, True)
        c_merovingian = Column.objects.filter(column_name='Merovingian')[0]
        self.assertEqual(c_merovingian.is_extra_data, True)
        self.assertEqual(c_merovingian.table_name, 'TaxLotState')

        # Check the database for the mapped columns since create_mappings doesn't return anything!
        cm = ColumnMapping.objects.filter(super_organization=self.fake_org,
                                          column_raw__in=[c_wookiee]).first()

        column = cm.column_mapped.first()
        self.assertEqual(column.is_extra_data, True)
        self.assertEqual(column.table_name, "PropertyState")
        self.assertEqual(column.column_name, "Dothraki")

    def test_save_columns(self):
        # create

        ps = PropertyState.objects.create(
            organization=self.fake_org,
            extra_data={'a': 123, 'lab': 'hawkins national laboratory'}
        )
        Column.save_column_names(ps)

        c = Column.objects.filter(column_name='lab')[0]

        self.assertEqual(c.is_extra_data, True)
        self.assertEqual(c.table_name, 'PropertyState')
        self.assertEqual(ps.extra_data['lab'], 'hawkins national laboratory')


class TestColumnMapping(TestCase):
    """Test ColumnMapping utility methods."""

    def setUp(self):
        foo_col = seed_models.Column.objects.create(column_name="foo")
        bar_col = seed_models.Column.objects.create(column_name="bar")
        baz_col = seed_models.Column.objects.create(column_name="baz")

        dm = seed_models.ColumnMapping.objects.create()
        dm.column_raw.add(foo_col)
        dm.column_mapped.add(baz_col)

        cm = seed_models.ColumnMapping.objects.create()
        cm.column_raw.add(foo_col, bar_col)
        cm.column_mapped.add(baz_col)

        self.directMapping = dm
        self.concatenatedMapping = cm

    def test_is_direct(self):
        self.assertEqual(self.directMapping.is_direct(), True)
        self.assertEqual(self.concatenatedMapping.is_direct(), False)

    def test_is_concatenated(self):
        self.assertEqual(self.directMapping.is_concatenated(), False)
        self.assertEqual(self.concatenatedMapping.is_concatenated(), True)
