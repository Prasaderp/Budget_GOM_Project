"""Database models for scheme 0029."""
from sqlalchemy import Column, Integer, String, BigInteger, CHAR, CheckConstraint, UniqueConstraint

from src.database import Base


class DistrictRevenue0029(Base):
    __tablename__ = "district_revenue_0029"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="0029", server_default="0029", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="0029", server_default="0029", index=True)

    table_section_code = Column(String(20), nullable=False, index=True)
    district = Column(String(100), nullable=False)

    actual_2017_18 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_2018_19 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_2019_20 = Column(BigInteger, nullable=False, default=0, server_default="0")

    budget_estimate_2020_21 = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate_2020_21 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_2021_22 = Column(BigInteger, nullable=False, default=0, server_default="0")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "table_section_code",
            "district",
            name="uq_district_rev_0029_natural_key",
        ),
        CheckConstraint("actual_2017_18 >= 0", name="chk_actual_1718_non_negative_0029"),
        CheckConstraint("actual_2018_19 >= 0", name="chk_actual_1819_non_negative_0029"),
        CheckConstraint("actual_2019_20 >= 0", name="chk_actual_1920_non_negative_0029"),
        CheckConstraint("budget_estimate_2020_21 >= 0", name="chk_budget_est_2021_non_negative_0029"),
        CheckConstraint("revised_estimate_2020_21 >= 0", name="chk_revised_est_2021_non_negative_0029"),
        CheckConstraint("budget_estimate_2021_22 >= 0", name="chk_be_2122_non_negative_0029"),
    )


class DistrictRevenue0029Section3(Base):
    __tablename__ = "district_revenue_0029_section3"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="0029", server_default="0029", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="0029", server_default="0029", index=True)

    table_section_code = Column(String(20), nullable=False, index=True)

    actual_2014_15 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_2015_16 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_2016_17 = Column(BigInteger, nullable=False, default=0, server_default="0")

    budget_estimate_2017_18 = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate_2017_18 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_2018_19 = Column(BigInteger, nullable=False, default=0, server_default="0")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "table_section_code",
            name="uq_district_rev_0029_s3_natural_key",
        ),
        CheckConstraint("actual_2014_15 >= 0", name="chk_actual_1415_non_negative_0029_s3"),
        CheckConstraint("actual_2015_16 >= 0", name="chk_actual_1516_non_negative_0029_s3"),
        CheckConstraint("actual_2016_17 >= 0", name="chk_actual_1617_non_negative_0029_s3"),
        CheckConstraint("budget_estimate_2017_18 >= 0", name="chk_budget_est_1718_non_negative_0029_s3"),
        CheckConstraint("revised_estimate_2017_18 >= 0", name="chk_revised_est_1718_non_negative_0029_s3"),
        CheckConstraint("budget_estimate_2018_19 >= 0", name="chk_be_1819_non_negative_0029_s3"),
    )


class DistrictRevenue0029Section4(Base):
    __tablename__ = "district_revenue_0029_section4"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="0029", server_default="0029", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="0029", server_default="0029", index=True)

    table_section_code = Column(String(20), nullable=False, index=True)

    actual_2011_12 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_2012_13 = Column(BigInteger, nullable=False, default=0, server_default="0")
    actual_2013_14 = Column(BigInteger, nullable=False, default=0, server_default="0")

    budget_estimate_2014_15 = Column(BigInteger, nullable=False, default=0, server_default="0")
    revised_estimate_2014_15 = Column(BigInteger, nullable=False, default=0, server_default="0")
    budget_estimate_2015_16 = Column(BigInteger, nullable=False, default=0, server_default="0")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "table_section_code",
            name="uq_district_rev_0029_s4_natural_key",
        ),
        CheckConstraint("actual_2011_12 >= 0", name="chk_actual_1112_non_negative_0029_s4"),
        CheckConstraint("actual_2012_13 >= 0", name="chk_actual_1213_non_negative_0029_s4"),
        CheckConstraint("actual_2013_14 >= 0", name="chk_actual_1314_non_negative_0029_s4"),
        CheckConstraint("budget_estimate_2014_15 >= 0", name="chk_budget_est_1415_non_negative_0029_s4"),
        CheckConstraint("revised_estimate_2014_15 >= 0", name="chk_revised_est_1415_non_negative_0029_s4"),
        CheckConstraint("budget_estimate_2015_16 >= 0", name="chk_be_1516_non_negative_0029_s4"),
    )


class DistrictRevenue0029JamaTalmel(Base):
    __tablename__ = "district_revenue_0029_jama_talmel"

    id = Column(Integer, primary_key=True, index=True)

    fiscal_year = Column(CHAR(7), nullable=False, index=True)
    scheme_code = Column(String(10), nullable=False, default="0029", server_default="0029", index=True)
    sub_scheme_code = Column(String(15), nullable=False, default="0029", server_default="0029", index=True)

    table_section_code = Column(String(20), nullable=False, index=True)

    mumbai_city_deposit = Column(BigInteger, nullable=False, default=0, server_default="0")
    mumbai_city_reconciliation = Column(BigInteger, nullable=False, default=0, server_default="0")
    
    mumbai_suburban_deposit = Column(BigInteger, nullable=False, default=0, server_default="0")
    mumbai_suburban_reconciliation = Column(BigInteger, nullable=False, default=0, server_default="0")
    
    thane_deposit = Column(BigInteger, nullable=False, default=0, server_default="0")
    thane_reconciliation = Column(BigInteger, nullable=False, default=0, server_default="0")
    
    raigad_deposit = Column(BigInteger, nullable=False, default=0, server_default="0")
    raigad_reconciliation = Column(BigInteger, nullable=False, default=0, server_default="0")
    
    ratnagiri_deposit = Column(BigInteger, nullable=False, default=0, server_default="0")
    ratnagiri_reconciliation = Column(BigInteger, nullable=False, default=0, server_default="0")
    
    sindhudurg_deposit = Column(BigInteger, nullable=False, default=0, server_default="0")
    sindhudurg_reconciliation = Column(BigInteger, nullable=False, default=0, server_default="0")

    remarks = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year",
            "sub_scheme_code",
            "table_section_code",
            name="uq_district_rev_0029_jt_natural_key",
        ),
        CheckConstraint("mumbai_city_deposit >= 0", name="chk_mc_deposit_non_negative_0029_jt"),
        CheckConstraint("mumbai_city_reconciliation >= 0", name="chk_mc_recon_non_negative_0029_jt"),
        CheckConstraint("mumbai_suburban_deposit >= 0", name="chk_ms_deposit_non_negative_0029_jt"),
        CheckConstraint("mumbai_suburban_reconciliation >= 0", name="chk_ms_recon_non_negative_0029_jt"),
        CheckConstraint("thane_deposit >= 0", name="chk_th_deposit_non_negative_0029_jt"),
        CheckConstraint("thane_reconciliation >= 0", name="chk_th_recon_non_negative_0029_jt"),
        CheckConstraint("raigad_deposit >= 0", name="chk_rg_deposit_non_negative_0029_jt"),
        CheckConstraint("raigad_reconciliation >= 0", name="chk_rg_recon_non_negative_0029_jt"),
        CheckConstraint("ratnagiri_deposit >= 0", name="chk_rt_deposit_non_negative_0029_jt"),
        CheckConstraint("ratnagiri_reconciliation >= 0", name="chk_rt_recon_non_negative_0029_jt"),
        CheckConstraint("sindhudurg_deposit >= 0", name="chk_sd_deposit_non_negative_0029_jt"),
        CheckConstraint("sindhudurg_reconciliation >= 0", name="chk_sd_recon_non_negative_0029_jt"),
    )


SCHEME_CODE = "0029"
SUB_SCHEME_CODE = "0029"

