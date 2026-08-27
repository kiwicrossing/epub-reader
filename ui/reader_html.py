def build_reader_html(content, font_size):
    """Build the styled HTML used by the reader."""
    return f"""
    <html>
    <head>
    <style>
        html {{
            overflow-x: hidden;
            overflow-y: hidden;
            background-color: #fef2f1;
        }}

        body {{
            width: min(90%, 700px);
            margin: 60px auto;
            padding: 50px 40px;

            background: white;
            box-sizing: border-box;
            border: 1px solid #fad3d1;
            border-radius: 10px;

            box-shadow:
                0 4px 15px rgba(63, 18, 25, 0.08);

            font-family: Georgia, serif;
            font-size: {font_size}px;
            color: #3f1219;
            line-height: 1.7;

            overflow: hidden;
        }}

        img {{
            max-width: 100%;
        }}

        h1, h2, h3 {{
            color: #3f1219;
        }}

        a {{
            color: #8d4a58;
        }}

        blockquote {{
            border-left: 4px solid #fec0c4;
            padding-left: 15px;
            color: #5f3f45;
        }}

        hr {{
            border: none;
            border-top: 1px solid #fad3d1;
        }}
    </style>
    </head>

    <body>
        {content}
    </body>
    </html>
    """