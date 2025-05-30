import os
import json
import logging
from datetime import datetime
from email_processor import WixEmailProcessor
from github_uploader import GitHubUploader
from url_generator import URLGenerator

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/main_processing.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    logger.info("Starting Wix traffic data processing workflow")
    
    try:
        # Initialize processors
        email_processor = WixEmailProcessor()
        github_uploader = GitHubUploader(
            repo_name=os.getenv('REPO_NAME'),
            organization=os.getenv('REPO_ORGANIZATION')
        )
        url_generator = URLGenerator(
            organization=os.getenv('REPO_ORGANIZATION'),
            repository=os.getenv('REPO_NAME')
        )
        
        # Process emails
        logger.info("Connecting to email account")
        with email_processor.connect_to_mailbox() as mailbox:
            messages = email_processor.search_wix_reports(mailbox)
            
            all_processed_data = []
            uploaded_files = []
            
            for message in messages:
                processed_attachments = email_processor.process_email_attachments(message)
                
                for attachment_data in processed_attachments:
                    # Extract and process traffic data
                    traffic_summary = email_processor.extract_traffic_data(attachment_data['data'])
                    
                    # Create comprehensive data package
                    data_package = {
                        'source_email': {
                            'subject': attachment_data['email_subject'],
                            'date': attachment_data['email_date']
                        },
                        'processing_info': {
                            'processed_date': attachment_data['processed_date'],
                            'filename': attachment_data['filename']
                        },
                        'traffic_data': traffic_summary,
                        'raw_data': attachment_data['data'].to_dict('records')
                    }
                    
                    all_processed_data.append(data_package)
            
            # Save processed data locally
            if all_processed_data:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                local_file = f"data/processed/wix_traffic_report_{timestamp}.json"
                
                with open(local_file, 'w') as f:
                    json.dump(all_processed_data, f, indent=2, default=str)
                
                # Upload to GitHub
                repo_path = f"traffic_data/wix_report_{timestamp}.json"
                raw_url = github_uploader.upload_file(local_file, repo_path)
                
                uploaded_files.append({
                    'local_path': local_file,
                    'repo_path': repo_path,
                    'raw_url': raw_url,
                    'upload_time': datetime.now().isoformat()
                })
                
                logger.info(f"Successfully processed {len(all_processed_data)} data packages")
            else:
                logger.info("No new Wix traffic data found")
        
        # Generate URL summary
        if uploaded_files:
            summary_url = github_uploader.create_summary_file(uploaded_files)
            
            # Generate URL lists for Claude integration
            file_paths = [item['repo_path'] for item in uploaded_files]
            url_list_file = url_generator.generate_url_list(file_paths)
            
            # Upload URL list to repository
            url_list_repo_path = f"url_lists/urls_{datetime.now().strftime('%Y%m%d')}.txt"
            github_uploader.upload_file(url_list_file, url_list_repo_path)
            
            logger.info(f"Generated URL list with {len(file_paths)} URLs")
            logger.info(f"Summary available at: {summary_url}")
        
        logger.info("Wix traffic data processing completed successfully")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise

if __name__ == "__main__":
    main()