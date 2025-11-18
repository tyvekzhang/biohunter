"""
TargetMining Tool - A comprehensive tool for extracting therapeutic targets from PubMed literature

This tool integrates PubMed querying, MEDLINE parsing, and LLM-based target extraction
to generate gene lists from biomedical literature.
"""

import os
import time
import subprocess
from fastlib import ConfigManager
import pandas as pd
import io
import re
from typing import List, Optional, Tuple
from pathlib import Path
from Bio import Medline
from openai import OpenAI
from fastlib.logging import logger

from src.main.app.agent.llm_config import LLMConfig


llm_config: LLMConfig = ConfigManager.get_config_instance("llm")


class TargetMiningConfig:
    """Configuration class for TargetMining tool"""

    def __init__(self):
        logger.info("Initializing TargetMiningConfig")
        # LLM Configuration
        self.api_key = llm_config.api_key
        self.base_url = llm_config.base_url
        self.model = llm_config.model

        # Processing Configuration
        self.batch_size = 10
        self.max_retries = 3
        self.retry_delay = 2
        
        # New: Top articles limit based on impact factor
        self.top_articles_limit = 100
        self.jcr_file_path = os.path.join(os.path.dirname(__file__), "JCR.xlsx")

        # Output Configuration
        self.output_format = "csv"
        self.include_pmids = True
        self.deduplicate = True

        # Default prompt template
        self.prompt_template = self._load_default_prompt()
        logger.info("TargetMiningConfig initialized successfully")

    def _load_default_prompt(self) -> str:
        """Load default prompt template"""
        logger.info("Loading default prompt template")
        prompt_path = Path(__file__).parent / "prompt" / "prompt.txt"
        if prompt_path.exists():
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    logger.info(f"Loaded prompt template from file: {prompt_path}")
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to load prompt template from file: {e}")
                return self._get_fallback_prompt()
        else:
            logger.warning(
                f"Prompt template file not found at: {prompt_path}, using fallback"
            )
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """Fallback prompt if file not found"""
        logger.info("Using fallback prompt template")
        return """Please read the following abstract and extract all the potential therapeutic targets or therapy-related molecules mentioned in the text. "Therapeutic targets or therapy-related molecules" include, but are not limited to:
* Tumor surface antigens (such as glycolipids, proteins, cytokine receptors, etc.)
* Molecules targeted by CAR-T cells, antibodies, drugs, and other therapeutic agents
* Molecules related to immunotherapy targets
Requirements:
Please organize your extracted results into the following table format with fixed headers:
| Target/Molecule(Name only)                  | Target/Molecule(Full name)                  | Role/Description                                  | Therapeutic Relevance                                  |
Where:
* Target/Molecule: The name of the molecule, antigen, receptor, or relevant cellular process.
* Role/Description: A concise description of the molecule's biological role or involvement in cancer or therapy.
* Therapeutic Relevance: Explanation of why this molecule or process is a potential therapeutic target or how it relates to therapy.
Please output only the table in markdown format without additional commentary."""


class JCRImpactFactorLoader:
    """Load and manage journal impact factor data from JCR.xlsx"""
    
    def __init__(self, jcr_file_path: str):
        self.jcr_file_path = jcr_file_path
        self.journal_if_map = {}
        self._load_jcr_data()
    
    def _load_jcr_data(self):
        """Load JCR data and create journal-IF mapping"""
        logger.info(f"Loading JCR data from: {self.jcr_file_path}")
        
        if not os.path.exists(self.jcr_file_path):
            logger.warning(f"JCR file not found: {self.jcr_file_path}")
            return
        
        try:
            # Read JCR Excel file
            df = pd.read_excel(self.jcr_file_path)
            
            # Check for required columns
            required_cols = ["名字", "缩写", "2023最新IF"]
            for col in required_cols:
                if col not in df.columns:
                    logger.warning(f"Required column '{col}' not found in JCR file")
                    return
            
            # Create mapping for both full name and abbreviation
            for _, row in df.iterrows():
                journal_name = str(row["名字"]).strip().upper()
                journal_abbrev = str(row["缩写"]).strip().upper()
                impact_factor = float(row["2023最新IF"])
                
                self.journal_if_map[journal_name] = impact_factor
                self.journal_if_map[journal_abbrev] = impact_factor
            
            logger.info(f"Loaded {len(self.journal_if_map)} journal impact factors")
            
        except Exception as e:
            logger.error(f"Error loading JCR data: {e}")
    
    def get_impact_factor(self, journal_name: str) -> float:
        """Get impact factor for a journal"""
        if not journal_name:
            return 0.0
        
        # Try exact match first
        journal_upper = journal_name.strip().upper()
        if journal_upper in self.journal_if_map:
            return self.journal_if_map[journal_upper]
        
        # Try partial match
        for key, value in self.journal_if_map.items():
            if journal_upper in key or key in journal_upper:
                return value
        
        return 0.0


class PubMedQueryExecutor:
    """Handles PubMed query execution and MEDLINE file retrieval"""

    def __init__(self, config: TargetMiningConfig):
        self.config = config
        logger.info("PubMedQueryExecutor initialized")

    def execute_query(self, query: str, output_dir: str) -> str:
        """
        Execute PubMed query and return path to MEDLINE file

        Args:
            query: PubMed query string
            output_dir: Directory to save results

        Returns:
            Path to the generated MEDLINE file
        """
        
        os.makedirs(output_dir, exist_ok=True)
        medline_file = os.path.join(output_dir, "query_results.medline")

        # Check if EDirect tools are available
        if not self._check_edirect_available():
            logger.error("EDirect tools not found")
            raise RuntimeError(
                "EDirect tools not found. Please install NCBI EDirect tools or provide a MEDLINE file directly."
            )

        # Execute the query using EDirect
        try:
            cmd = f'esearch -db pubmed -query "{query}" | efetch -format medline'
            logger.info(f"Executing command: {cmd}")

            with open(medline_file, "w", encoding="utf-8") as f:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(
                        f"Query execution failed with return code {result.returncode}: {result.stderr}"
                    )
                    raise RuntimeError(f"Query execution failed: {result.stderr}")
                f.write(result.stdout)

            # Verify the file was created and has content
            if not os.path.exists(medline_file):
                logger.error("MEDLINE file was not created")
                raise RuntimeError("MEDLINE file was not created")

            file_size = os.path.getsize(medline_file)
            if file_size == 0:
                logger.warning("MEDLINE file is empty - no results found for query")
                raise RuntimeError(
                    "No results found for the query or query execution failed"
                )

            logger.info(
                f"Query results saved to: {medline_file} (size: {file_size} bytes)"
            )
            return medline_file

        except Exception as e:
            logger.exception(f"Error executing PubMed query: {e}")
            raise

    def _check_edirect_available(self) -> bool:
        """Check if EDirect tools are available"""
        try:
            subprocess.run(["esearch", "-help"], capture_output=True, check=True)
            logger.info("EDirect tools are available")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"EDirect tools not available: {e}")
            return False


class MedlineParser:
    """Handles parsing of MEDLINE format files"""

    def __init__(self, config: TargetMiningConfig):
        self.config = config
        logger.info("MedlineParser initialized")

    def parse_medline_file(self, file_path: str) -> pd.DataFrame:
        """
        Parse MEDLINE file and extract metadata

        Args:
            file_path: Path to MEDLINE file

        Returns:
            DataFrame with PMID, Title, Abstract, and Journal columns
        """
        logger.info(f"Parsing MEDLINE file: {file_path}")
        records = []

        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                medline_records = Medline.parse(handle)
                record_count = 0
                skipped_count = 0

                for record in medline_records:
                    record_count += 1
                    pmid = record.get("PMID", "")
                    title = record.get("TI", "")
                    abstract = record.get("AB", "")
                    
                    # Extract journal information
                    journal = record.get("TA", "")  # Journal Title Abbreviation
                    if not journal:
                        journal = record.get("JT", "")  # Journal Title
                    
                    # Extract publication date
                    pub_date = record.get("DP", "")  # Date of Publication

                    # Skip records without title or abstract
                    if not title and not abstract:
                        skipped_count += 1
                        logger.info(f"Skipping record {pmid}: no title or abstract")
                        continue

                    records.append({
                        "PMID": pmid, 
                        "Title": title, 
                        "Abstract": abstract,
                        "Journal": journal,
                        "Publication_Date": pub_date
                    })

            df = pd.DataFrame(records)
            logger.info(
                f"Parsed {record_count} records from MEDLINE file ({skipped_count} skipped, {len(df)} valid)"
            )

            if len(df) == 0:
                logger.warning("No valid records found in MEDLINE file")

            return df

        except Exception as e:
            logger.exception(f"Error parsing MEDLINE file: {e}")
            raise


class ImpactFactorFilter:
    """Filter and rank articles based on journal impact factors"""
    
    def __init__(self, jcr_loader: JCRImpactFactorLoader):
        self.jcr_loader = jcr_loader
    
    def rank_articles_by_impact_factor(self, df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
        """
        Rank articles by journal impact factor and return top N
        
        Args:
            df: DataFrame with articles
            top_n: Number of top articles to return
        
        Returns:
            Filtered and sorted DataFrame
        """
        logger.info(f"Ranking {len(df)} articles by impact factor")
        
        # Add impact factor column
        df["Impact_Factor"] = df["Journal"].apply(self.jcr_loader.get_impact_factor)
        
        # Sort by impact factor (descending)
        df_sorted = df.sort_values("Impact_Factor", ascending=False)
        
        # Log statistics
        logger.info(f"Impact factor statistics:")
        logger.info(f"  - Articles with IF > 0: {len(df_sorted[df_sorted['Impact_Factor'] > 0])}")
        logger.info(f"  - Max IF: {df_sorted['Impact_Factor'].max():.2f}")
        logger.info(f"  - Mean IF: {df_sorted['Impact_Factor'].mean():.2f}")
        
        # Get top N articles
        df_top = df_sorted.head(top_n)
        logger.info(f"Selected top {len(df_top)} articles for processing")
        
        # Log selected articles
        for idx, row in df_top.head(10).iterrows():
            logger.info(f"  PMID: {row['PMID']}, Journal: {row['Journal']}, IF: {row['Impact_Factor']:.2f}")
        
        return df_top


class LLMTargetExtractor:
    """Handles LLM-based target extraction from literature"""

    def __init__(self, config: TargetMiningConfig):
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        logger.info(f"LLMTargetExtractor initialized with model: {config.model}")

    def extract_targets_from_dataframe(
        self, df: pd.DataFrame, output_dir: str
    ) -> pd.DataFrame:
        """
        Extract targets from DataFrame using LLM in batches

        Args:
            df: DataFrame with PMID, Title, Abstract columns
            output_dir: Directory to save batch results

        Returns:
            DataFrame with extracted targets
        """
        logger.info(f"Starting target extraction from DataFrame with {len(df)} records")
        batch_output_dir = os.path.join(output_dir, "batch_results")
        os.makedirs(batch_output_dir, exist_ok=True)

        # Process in batches
        total_rows = len(df)
        num_batches = (
            total_rows + self.config.batch_size - 1
        ) // self.config.batch_size

        logger.info(
            f"Processing {total_rows} records in {num_batches} batches (batch size: {self.config.batch_size})"
        )

        # Process each batch
        successful_batches = 0
        for batch_num in range(num_batches):
            start_idx = batch_num * self.config.batch_size
            end_idx = min(start_idx + self.config.batch_size, total_rows)

            batch_file = os.path.join(batch_output_dir, f"batch_{batch_num + 1}.csv")
            if os.path.exists(batch_file):
                logger.info(
                    f"Batch {batch_num + 1}/{num_batches} already processed, skipping"
                )
                successful_batches += 1
                continue

            logger.info(
                f"Processing batch {batch_num + 1}/{num_batches} (rows {start_idx}-{end_idx-1})"
            )

            batch_df = df.iloc[start_idx:end_idx]

            try:
                result_batch = self._process_batch(batch_df)
                if not result_batch.empty:
                    result_batch.to_csv(batch_file, index=False)
                    logger.info(
                        f"Batch {batch_num + 1} completed with {len(result_batch)} results"
                    )
                    successful_batches += 1
                else:
                    logger.warning(f"Batch {batch_num + 1} produced no results")

            except Exception as e:
                logger.error(f"Error processing batch {batch_num + 1}: {e}")
                continue

        logger.info(
            f"Batch processing completed: {successful_batches}/{num_batches} batches successful"
        )

        # Combine all batch results
        return self._combine_batch_results(batch_output_dir, num_batches)

    def _process_batch(self, batch_df: pd.DataFrame) -> pd.DataFrame:
        """Process a single batch of records"""
        logger.info(f"Processing batch with {len(batch_df)} records")
        all_results = []
        successful_records = 0
        failed_records = 0

        for _, row in batch_df.iterrows():
            try:
                result = self._extract_targets_from_record(row)
                if result is not None and not result.empty:
                    result["Source_PMID"] = int(row["PMID"]) if row["PMID"] else None
                    result["Journal"] = row.get("Journal", "")
                    result["Impact_Factor"] = row.get("Impact_Factor", 0.0)
                    all_results.append(result)
                    successful_records += 1
                else:
                    logger.info(
                        f"No targets extracted from PMID: {row.get('PMID', 'unknown')}"
                    )
                    failed_records += 1

            except Exception as e:
                logger.error(f"Error processing PMID {row.get('PMID', 'unknown')}: {e}")
                failed_records += 1
                continue

        logger.info(
            f"Batch processed: {successful_records} successful, {failed_records} failed"
        )

        if all_results:
            return pd.concat(all_results, ignore_index=True)
        else:
            return pd.DataFrame()

    def _extract_targets_from_record(self, row: pd.Series) -> Optional[pd.DataFrame]:
        """Extract targets from a single record"""
        pmid = row.get("PMID", "unknown")
        title = str(row.get("Title", ""))
        abstract = str(row.get("Abstract", ""))
        journal = row.get("Journal", "")
        impact_factor = row.get("Impact_Factor", 0.0)

        if not title and not abstract:
            logger.info(f"Skipping record {pmid}: no title or abstract")
            return None

        logger.info(f"Extracting targets from PMID: {pmid} (Journal: {journal}, IF: {impact_factor:.2f})")

        # Construct prompt
        messages = [
            {
                "role": "system",
                "content": "You are an expert in information extraction from scientific literature.",
            },
            {
                "role": "user",
                "content": f"Input Provided:\n'''\nTitle: {title}\nAbstract: {abstract}\n'''\nTask: {self.config.prompt_template}",
            },
        ]

        # Make API call with retries
        for attempt in range(self.config.max_retries):
            try:
                logger.info(
                    f"Making LLM API call for PMID {pmid} (attempt {attempt + 1})"
                )
                completion = self.client.chat.completions.create(
                    model=self.config.model, messages=messages
                )
                answer = completion.choices[0].message.content

                if answer:
                    result_df = self._parse_llm_response(answer)
                    if not result_df.empty:
                        logger.info(
                            f"Extracted {len(result_df)} targets from PMID: {pmid}"
                        )
                        return result_df
                    else:
                        logger.info(
                            f"No targets parsed from LLM response for PMID: {pmid}"
                        )
                else:
                    logger.info(f"Empty response from LLM for PMID: {pmid}")

                break

            except Exception as e:
                logger.warning(
                    f"API call failed for PMID {pmid}, attempt {attempt + 1}: {e}"
                )
                if attempt < self.config.max_retries - 1:
                    logger.info(
                        f"Retrying after delay of {self.config.retry_delay} seconds"
                    )
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error(
                        f"Failed to process PMID {pmid} after {self.config.max_retries} attempts"
                    )

        return None

    def _parse_llm_response(self, response: str) -> pd.DataFrame:
        """Parse LLM response into structured DataFrame"""
        logger.info("Parsing LLM response")
        try:
            # Find table data using regex
            data = re.findall(r"(?m)^\|.*?\|$", response)
            data = [line for line in data if "---" not in line]

            if not data:
                logger.info("No table data found in LLM response")
                return pd.DataFrame()

            logger.info(f"Found {len(data)} table rows in LLM response")
            table_data_str = "\n".join(data)
            table_data_io = io.StringIO(table_data_str)

            # Parse table
            table_data = pd.read_csv(
                table_data_io,
                sep="\|",
                engine="python",
                header=0,
                skipinitialspace=True,
            )

            # Clean up columns
            table_data = table_data.iloc[:, 1:-1]  # Remove first and last empty columns
            table_data.columns = table_data.columns.str.strip()

            logger.info(
                f"Successfully parsed {len(table_data)} targets from LLM response"
            )
            return table_data

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.info(
                f"Response content: {response[:500] + '...' if len(response) > 500 else response}"
            )
            return pd.DataFrame()

    def _combine_batch_results(
        self, batch_output_dir: str, num_batches: int
    ) -> pd.DataFrame:
        """Combine all batch results into final DataFrame"""
        logger.info(f"Combining batch results from {num_batches} batches")
        all_batches = []
        loaded_batches = 0

        for batch_num in range(num_batches):
            batch_file = os.path.join(batch_output_dir, f"batch_{batch_num + 1}.csv")
            if os.path.exists(batch_file):
                try:
                    batch_df = pd.read_csv(batch_file)
                    if not batch_df.empty:
                        all_batches.append(batch_df)
                        loaded_batches += 1
                        logger.info(
                            f"Loaded batch {batch_num + 1} with {len(batch_df)} records"
                        )
                    else:
                        logger.info(f"Batch {batch_num + 1} is empty")
                except Exception as e:
                    logger.error(f"Error reading batch file {batch_file}: {e}")

        if all_batches:
            final_df = pd.concat(all_batches, ignore_index=True)
            logger.info(
                f"Combined {loaded_batches} batches into {len(final_df)} total records"
            )
            return final_df
        else:
            logger.warning("No batch results found to combine")
            return pd.DataFrame()


class TargetMiningTool:
    """
    Main TargetMining tool class that orchestrates the entire pipeline
    """

    def __init__(self, config: Optional[TargetMiningConfig] = None):
        """
        Initialize TargetMining tool

        Args:
            config: Optional configuration object. If None, default config is used.
        """
        self.config = config or TargetMiningConfig()
        self.query_executor = PubMedQueryExecutor(self.config)
        self.medline_parser = MedlineParser(self.config)
        self.llm_extractor = LLMTargetExtractor(self.config)
        
        # Initialize JCR loader and impact factor filter
        self.jcr_loader = JCRImpactFactorLoader(self.config.jcr_file_path)
        self.if_filter = ImpactFactorFilter(self.jcr_loader)
        
        logger.info("TargetMiningTool initialized successfully")

    def mine_targets(
        self, query: str, output_dir: str = None, medline_file: str = None
    ) -> Tuple[List[str], pd.DataFrame]:
        """
        Main method to mine therapeutic targets from PubMed query

        Args:
            query: PubMed query string (if medline_file not provided)
            output_dir: Output directory for results (default: ./output)
            medline_file: Path to existing MEDLINE file (optional)

        Returns:
            Tuple of (gene_list, full_results_dataframe)
        """
        start_time = time.time()

        if output_dir is None:
            output_dir = f"output_{int(time.time())}"

        os.makedirs(output_dir, exist_ok=True)

        logger.info("=== TargetMining Tool Started ===")
        logger.info(f"Output directory: {output_dir}")

        try:
            # Step 1: Get MEDLINE data
            if medline_file and os.path.exists(medline_file):
                logger.info(f"Using provided MEDLINE file: {medline_file}")
                medline_path = medline_file
            else:
                logger.info(f"Executing PubMed query: {query}")
                medline_path = self.query_executor.execute_query(query, output_dir)

            # Step 2: Parse MEDLINE file
            logger.info("Parsing MEDLINE file...")
            df = self.medline_parser.parse_medline_file(medline_path)

            if df.empty:
                logger.warning("No records found in MEDLINE file")
                return [], pd.DataFrame()

            # Save all parsed data
            all_parsed_file = os.path.join(output_dir, "all_parsed_records.csv")
            df.to_csv(all_parsed_file, index=False, encoding="utf-8")
            logger.info(f"All parsed records saved to: {all_parsed_file}")

            # Step 3: Filter by impact factor and select top articles
            logger.info(f"Filtering top {self.config.top_articles_limit} articles by impact factor...")
            df_filtered = self.if_filter.rank_articles_by_impact_factor(
                df, top_n=self.config.top_articles_limit
            )
            
            # Save filtered articles
            filtered_file = os.path.join(output_dir, "top_articles_by_if.csv")
            df_filtered.to_csv(filtered_file, index=False, encoding="utf-8")
            logger.info(f"Top articles saved to: {filtered_file}")
            
            # Log statistics
            logger.info(f"Article selection statistics:")
            logger.info(f"  - Total articles parsed: {len(df)}")
            logger.info(f"  - Articles selected for processing: {len(df_filtered)}")
            logger.info(f"  - Average IF of selected articles: {df_filtered['Impact_Factor'].mean():.2f}")

            # Step 4: Extract targets using LLM (only from top articles)
            logger.info(f"Extracting targets from {len(df_filtered)} top articles...")
            results_df = self.llm_extractor.extract_targets_from_dataframe(
                df_filtered, output_dir
            )

            if results_df.empty:
                logger.warning("No targets extracted from literature")
                return [], pd.DataFrame()

            # Step 5: Generate final results
            logger.info("Generating final results...")
            gene_list, final_df = self._process_final_results(results_df, output_dir)

            execution_time = time.time() - start_time
            logger.info("=== TargetMining Completed ===")
            logger.info(f"Execution time: {execution_time:.2f} seconds")
            logger.info(f"Total unique targets found: {len(gene_list)}")
            logger.info(f"Results saved to: {output_dir}")
            
            # Print summary statistics
            self._print_summary_statistics(df, df_filtered, final_df)

            return gene_list, final_df

        except Exception as e:
            logger.exception(f"Target mining process failed: {e}")
            raise

    def _process_final_results(
        self, results_df: pd.DataFrame, output_dir: str
    ) -> Tuple[List[str], pd.DataFrame]:
        """Process and clean final results"""
        logger.info(f"Processing final results ({len(results_df)} initial records)")

        # Save raw results
        raw_results_file = os.path.join(output_dir, "raw_extraction_results.csv")
        results_df.to_csv(raw_results_file, index=False)
        logger.info(f"Raw results saved to: {raw_results_file}")

        # Clean and deduplicate if configured
        if (
            self.config.deduplicate
            and "Target/Molecule(Name only)" in results_df.columns
        ):
            logger.info("Deduplicating results...")
            # Clean target names
            results_df["Target/Molecule(Name only)"] = (
                results_df["Target/Molecule(Name only)"]
                .astype(str)
                .str.replace(r"\s{2,}", " ", regex=True)
                .str.strip()
            )

            # Remove empty or invalid entries
            initial_count = len(results_df)
            results_df = results_df[
                (results_df["Target/Molecule(Name only)"] != "")
                & (results_df["Target/Molecule(Name only)"] != "nan")
                & (results_df["Target/Molecule(Name only)"].notna())
            ]
            cleaned_count = len(results_df)

            # Deduplicate
            final_df = results_df.drop_duplicates(
                subset=["Target/Molecule(Name only)"], keep="first"
            )

            logger.info(
                f"Deduplication: {initial_count} -> {cleaned_count} -> {len(final_df)} records (initial -> cleaned -> deduplicated)"
            )
        else:
            final_df = results_df
            logger.info("Skipping deduplication")

        # Save final results
        final_results_file = os.path.join(output_dir, "final_target_results.csv")
        final_df.to_csv(final_results_file, index=False)

        # Generate gene list
        if "Target/Molecule(Name only)" in final_df.columns:
            gene_list = final_df["Target/Molecule(Name only)"].tolist()
            logger.info(f"Generated gene list with {len(gene_list)} entries")
        else:
            gene_list = []
            logger.warning(
                "No 'Target/Molecule(Name only)' column found for gene list generation"
            )

        # Save gene list
        gene_list_file = os.path.join(output_dir, "gene_list.txt")
        with open(gene_list_file, "w", encoding="utf-8") as f:
            for gene in gene_list:
                f.write(f"{gene}\n")

        logger.info(f"Gene list saved to: {gene_list_file}")
        logger.info(f"Final results saved to: {final_results_file}")

        return gene_list, final_df
    
    def _print_summary_statistics(self, df_all: pd.DataFrame, df_filtered: pd.DataFrame, df_final: pd.DataFrame):
        """Print summary statistics of the mining process"""
        logger.info("\n" + "="*50)
        logger.info("SUMMARY STATISTICS")
        logger.info("="*50)
        logger.info(f"Total articles retrieved: {len(df_all)}")
        logger.info(f"Articles selected by IF: {len(df_filtered)} (top {self.config.top_articles_limit})")
        
        if "Impact_Factor" in df_filtered.columns:
            logger.info(f"Impact Factor range of selected articles: {df_filtered['Impact_Factor'].min():.2f} - {df_filtered['Impact_Factor'].max():.2f}")
        
        if not df_final.empty:
            logger.info(f"Total targets extracted: {len(df_final)}")
            
            if "Journal" in df_final.columns:
                top_journals = df_final["Journal"].value_counts().head(5)
                logger.info("Top 5 journals contributing targets:")
                for journal, count in top_journals.items():
                    logger.info(f"  - {journal}: {count} targets")
        
        logger.info("="*50 + "\n")