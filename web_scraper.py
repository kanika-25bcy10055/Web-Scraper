# Note: Run pip install in a separate cell with !pip or %pip
# !pip install requests beautifulsoup4

import requests
from bs4 import BeautifulSoup

def scrape_movies(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Example selectors (might need adjustment for the actual website HTML)
        movie_listings = soup.find_all('div', class_='movie-item') 
        
        if not movie_listings:
            print("No movie listings found. Check your selectors.")
            return []

        movies_data = []
        for movie in movie_listings:
            # Example selectors
            title_element = movie.find('h2', class_='movie-title')
            rating_element = movie.find('span', class_='movie-rating')
            
            title = title_element.get_text(strip=True) if title_element else "N/A"
            rating = rating_element.get_text(strip=True) if rating_element else "N/A"
            movies_data.append({'Title': title, 'Rating': rating})
        return movies_data

    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == "__main__":
    # Replace with the actual URL of the website you want to scrape
    target_url = "http://publicdomainmovie.net/"
    print(f"Scraping data from: {target_url}")
    scraped_data = scrape_movies(target_url)

    if scraped_data:
        print("\n--- Scraped Movie Data ---")
        for movie in scraped_data:
            print(f"Title: {movie['Title']}, Rating: {movie['Rating']}")
    else:
        print("Failed to scrape data")