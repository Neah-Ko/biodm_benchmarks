# TODO
# generate customized templates
# for datasets take the group of the user as a responsible partner
# Create an in-memory output file for the new dataset workbook
# output = io.BytesIO()

# TODO
# temporary disabled because it does not seem to be used at the moment

# from pathlib import Path
# import xlsxwriter


# def generate_template(template_for, example_data):

#     # TODO
#     # add input validation

#     pf = Path(__file__).parents[1] / f"templates/
#           {template_for}_template.xlsx"

#     if pf.is_file() is False:
#         workbook = xlsxwriter.Workbook(pf)
#         worksheet = workbook.add_worksheet()

#         # Write some test data.
#         for row_num, columns in enumerate(example_data):
#             for col_num, cell_data in enumerate(columns):
#                 worksheet.write(row_num, col_num, cell_data)

#         workbook.close()
