"""GST state codes and the tax split used on invoices."""
from decimal import ROUND_HALF_UP, Decimal

GST_RATE = Decimal("0.18")

GST_STATES = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def tax_breakdown(amount_inclusive: Decimal, seller_state: str, place_of_supply: str) -> dict:
    """
    Splits a GST-inclusive amount. Intra-state supplies (customer in the seller's state)
    carry CGST + SGST at 9% each; inter-state supplies carry IGST at 18%.
    """
    amount = Decimal(amount_inclusive)
    taxable = _money(amount / (1 + GST_RATE))
    tax = _money(amount - taxable)
    intra_state = bool(seller_state) and seller_state == place_of_supply
    if intra_state:
        cgst = _money(tax / 2)
        return {"taxable": taxable, "lines": [("CGST (9%)", cgst), ("SGST (9%)", tax - cgst)], "total": amount}
    return {"taxable": taxable, "lines": [("IGST (18%)", tax)], "total": amount}
