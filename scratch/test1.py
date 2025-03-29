import bs4

element = """
<a href="javascript:void(0)">XCU Men 1:55 Category A&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337865"><a href="javascript:void(0)">XCU Men 1:55 Category B&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337866"><a href="javascript:void(0)">XCU Men 1:55 Category C&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337867"><a href="javascript:void(0)">XCU Men 1:55 Category D&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337868"><a href="javascript:void(0)">XCU Men 5:45 Category A&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337869"><a href="javascript:void(0)">XCU Men 5:45 Category B&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337870"><a href="javascript:void(0)">XCU Women 5:45 Category B&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337871"><a href="javascript:void(0)">XCU Men 5:45 Category C&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337872"><a href="javascript:void(0)">XCU Women 5:45 Category C&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337873"><a href="javascript:void(0)">XCU Men 5:45 Category D&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337874"><a href="javascript:void(0)">XCU Women 5:45 Category D&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337875"><a href="javascript:void(0)">XCU Men 8:55 Category A&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337876"><a href="javascript:void(0)">XCU Men 8:55 Category B&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337877"><a href="javascript:void(0)">XCU Men 8:55 Category C&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;<li id="race_1337878"><a href="javascript:void(0)">XCU Men 8:55 Category D&lt;\\/a&gt;<div><img \\="" alt="loading" src="\\/images\\/loading.gif" style="vertical-align:middle;margin-right:5px;"/>Loading...&lt;\\/div&gt;&lt;\\/li&gt;&lt;\\/ul&gt;&lt;\\/div&gt;<div id='\"SplitOverlay\"'>&lt;\\/div&gt;"}</div></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a></li></div></a>
"""

soup = bs4.BeautifulSoup(element, "html.parser")
# Find all links to extract category names
links = soup.find_all("a")
category_names = []

for link in links:
    # Extract just the category text without any extra elements
    category_text = link.get_text(strip=True)
    # Get text before the escaped closing tag if present
    if "<\\" in category_text:
        category_text = category_text.split("<\\")[0]
    category_names.append(category_text)

# Print the first category name
if category_names:
    print(f"First category: {category_names[0]}")
