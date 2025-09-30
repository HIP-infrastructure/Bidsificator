"""
BIDS Schema parser

Parses the BIDS schema JSON into usable Python objects.
Dynamically extracts information from the real BIDS schema structure.
"""

import re
from typing import Dict, Any, List
from collections import defaultdict
from .models import BidsEntity, BidsDatatype, EntityFormat


class BidsSchemaParser:
    """Parse BIDS schema JSON into Python objects"""
    
    def parse_entities(self, schema: dict) -> Dict[str, BidsEntity]:
        """Extract entity definitions from schema.objects.entities"""
        entities = {}
        
        entity_objects = schema.get("objects", {}).get("entities", {})
        
        for entity_key, entity_def in entity_objects.items():
            # Extract entity format from schema
            format_value = entity_def.get("format", "label")
            if format_value == "label":
                format_enum = EntityFormat.LABEL
                # For label format, use alphanumeric pattern
                pattern = r"[a-zA-Z0-9]+"
            elif format_value == "index":
                format_enum = EntityFormat.INDEX  
                # For index format, use numeric pattern
                pattern = r"[0-9]+"
            else:
                format_enum = EntityFormat.ALPHANUMERIC
                pattern = r"[a-zA-Z0-9]+"
            
            # Check if entity has enum values (restricted choices)
            enum_values = entity_def.get("enum")
            if enum_values:
                # Create pattern that matches any of the enum values
                escaped_values = [re.escape(v) for v in enum_values]
                pattern = f"({'|'.join(escaped_values)})"
            
            entities[entity_def["name"]] = BidsEntity(
                name=entity_def.get("display_name", entity_def["name"]),
                key=entity_def["name"],
                required=False,  # Will be determined by rules/context
                format=format_enum,
                pattern=pattern,
                description=entity_def.get("description", "")
            )
        
        return entities
    
    def parse_datatypes(self, schema: dict) -> Dict[str, BidsDatatype]:
        """Extract datatype definitions dynamically from schema rules and objects"""
        datatypes = {}
        
        # Get datatype objects for names and descriptions
        datatype_objects = schema.get("objects", {}).get("datatypes", {})
        
        # Extract datatype information from file rules
        datatype_info = self._extract_datatype_rules(schema)
        
        # Extract metadata requirements
        metadata_requirements = self._extract_metadata_requirements(schema)
        
        # Create datatype objects
        for dt_key, dt_def in datatype_objects.items():
            info = datatype_info.get(dt_key, {})
            
            datatypes[dt_key] = BidsDatatype(
                name=dt_key,
                allowed_entities=sorted(info.get('entities', set())),
                required_entities=sorted(info.get('required_entities', set())),
                suffixes=sorted(info.get('suffixes', set())),
                extensions=sorted(info.get('extensions', set())),
                metadata_requirements=metadata_requirements.get(dt_key, {})
            )
        
        return datatypes
    
    def _extract_datatype_rules(self, schema: dict) -> Dict[str, Dict[str, Any]]:
        """Extract datatype rules from schema.rules.files.raw"""
        datatype_info = defaultdict(lambda: {
            'suffixes': set(),
            'extensions': set(),
            'entities': set(),
            'required_entities': set(),
            'metadata': {}
        })
        
        # Process file rules
        files_raw = schema.get('rules', {}).get('files', {}).get('raw', {})
        
        for rule_name, rule_data in files_raw.items():
            if isinstance(rule_data, dict):
                for file_type, file_rule in rule_data.items():
                    if isinstance(file_rule, dict) and 'datatypes' in file_rule:
                        datatypes = file_rule.get('datatypes', [])
                        suffixes = file_rule.get('suffixes', [])
                        extensions = file_rule.get('extensions', [])
                        entities = file_rule.get('entities', {})
                        
                        for datatype in datatypes:
                            datatype_info[datatype]['suffixes'].update(suffixes)
                            datatype_info[datatype]['extensions'].update(extensions)
                            datatype_info[datatype]['entities'].update(entities.keys())
                            
                            # Track required entities
                            for entity, requirement in entities.items():
                                if requirement == 'required':
                                    datatype_info[datatype]['required_entities'].add(entity)
        
        return datatype_info
    
    def _extract_metadata_requirements(self, schema: dict) -> Dict[str, Dict[str, Any]]:
        """Extract metadata requirements dynamically from schema sidecar rules"""
        # Get all metadata objects with their definitions
        metadata_objects = schema.get("objects", {}).get("metadata", {})
        
        # Parse metadata requirements from sidecar rules (the real source of requirements)
        metadata_requirements = defaultdict(lambda: {"required": {}, "recommended": {}, "optional": {}})
        
        # Process sidecar rules - these contain the actual metadata requirements
        sidecar_rules = schema.get("rules", {}).get("sidecars", {})
        
        # Extract modality to datatype mappings from schema
        modality_to_datatype = self._extract_modality_mappings(schema)
        
        for modality, rules_dict in sidecar_rules.items():
            if modality in modality_to_datatype:
                datatypes = modality_to_datatype[modality]  # Now a list of datatypes
                
                # Apply rules to ALL datatypes for this modality (e.g., mri rules apply to anat, dwi, func, etc.)
                for datatype in datatypes:
                    for rule_name, rule_data in rules_dict.items():
                        if isinstance(rule_data, dict) and "fields" in rule_data:
                            fields = rule_data["fields"]
                            
                            # Extract field requirements
                            for field_name, field_rule in fields.items():
                                if field_name in metadata_objects:
                                    field_def = metadata_objects[field_name]
                                    
                                    # Parse requirement level
                                    if field_rule == "required":
                                        metadata_requirements[datatype]["required"][field_name] = field_def
                                    elif field_rule == "recommended":
                                        metadata_requirements[datatype]["recommended"][field_name] = field_def
                                    elif isinstance(field_rule, dict):
                                        level = field_rule.get("level", "optional")
                                        if level == "required":
                                            metadata_requirements[datatype]["required"][field_name] = field_def
                                        elif level == "recommended":
                                            metadata_requirements[datatype]["recommended"][field_name] = field_def
                                        else:
                                            metadata_requirements[datatype]["optional"][field_name] = field_def
                                    else:
                                        # Default to optional if not specified
                                        metadata_requirements[datatype]["optional"][field_name] = field_def
        
        # Also extract coordinate system requirements from JSON rules
        self._extract_coordinate_system_requirements(schema, metadata_requirements, metadata_objects)
        
        return dict(metadata_requirements)
    
    def _extract_modality_mappings(self, schema: dict) -> Dict[str, List[str]]:
        """Extract modality to datatype mappings from schema"""
        modalities = schema.get("rules", {}).get("modalities", {})
        
        # Create mapping from rule keys (modalities) to list of datatypes they should apply to
        # This handles both direct datatype rules and modality rules that apply to multiple datatypes
        mapping = {}
        
        for modality, mod_data in modalities.items():
            if isinstance(mod_data, dict) and "datatypes" in mod_data:
                datatypes = mod_data["datatypes"]
                # Map the modality to ALL of its constituent datatypes
                # E.g., "mri" maps to ["anat", "dwi", "func", "fmap", "perf"]
                mapping[modality] = datatypes
        
        # For sidecar and JSON rules, the keys are often datatypes themselves
        # So we also include direct datatype mappings
        datatypes = schema.get("objects", {}).get("datatypes", {})
        for datatype in datatypes.keys():
            mapping[datatype] = [datatype]  # Each datatype maps to itself as a list
            
        return mapping
    
    def _extract_coordinate_system_requirements(self, schema: dict, metadata_requirements: dict, metadata_objects: dict):
        """Extract coordinate system requirements from JSON rules"""
        json_rules = schema.get("rules", {}).get("json", {})
        
        # Extract modality to datatype mappings from schema
        modality_to_datatype = self._extract_modality_mappings(schema)
        
        for modality, rules_dict in json_rules.items():
            if modality in modality_to_datatype:
                datatypes = modality_to_datatype[modality]  # Now a list of datatypes
                
                # Apply rules to ALL datatypes for this modality
                for datatype in datatypes:
                    for rule_name, rule_data in rules_dict.items():
                        if isinstance(rule_data, dict) and "fields" in rule_data:
                            fields = rule_data["fields"]
                            
                            # Extract coordinate system field requirements
                            for field_name, field_rule in fields.items():
                                if field_name in metadata_objects:
                                    field_def = metadata_objects[field_name]
                                    
                                    # Parse requirement level
                                    if field_rule == "required":
                                        metadata_requirements[datatype]["required"][field_name] = field_def
                                    elif isinstance(field_rule, dict):
                                        level = field_rule.get("level", "optional")
                                        if level == "required":
                                            metadata_requirements[datatype]["required"][field_name] = field_def
                                        elif level == "recommended":
                                            metadata_requirements[datatype]["recommended"][field_name] = field_def
                                        else:
                                            metadata_requirements[datatype]["optional"][field_name] = field_def
    
    def parse_metadata(self, schema: dict) -> Dict[str, Any]:
        """Extract metadata field definitions from schema.objects.metadata"""
        return schema.get("objects", {}).get("metadata", {})
    
    def build_filename_templates(self, schema: dict) -> Dict[str, str]:
        """Build filename templates from schema rules"""
        templates = {}
        
        # Parse filename patterns from rules
        # For now, build a comprehensive template based on common entity order
        entity_objects = schema.get("objects", {}).get("entities", {})
        
        # Build template with all possible entities in logical order
        entity_order = [
            "subject", "session", "task", "acquisition", "ceagent", "reconstruction", 
            "direction", "run", "modality", "echo", "flip", "inversion", "mtransfer",
            "part", "processing", "space", "split", "recording", "chunk", "sample",
            "tracksys", "acq"  # acq for backwards compatibility
        ]
        
        template_parts = []
        for entity in entity_order:
            if entity in entity_objects:
                entity_key = entity_objects[entity]["name"]
                if entity_key == "subject":
                    template_parts.append(f"sub-{{{entity_key}}}")  # Subject is required
                else:
                    template_parts.append(f"[_{entity_key}-{{{entity_key}}}]")  # Optional entities
        
        basic_template = "".join(template_parts) + "_{suffix}{extension}"
        templates["basic"] = basic_template
        
        return templates
    
    def get_schema_version(self, schema: dict) -> str:
        """Get the BIDS schema version"""
        return schema.get("bids_version", "unknown")
    
    def get_schema_info(self, schema: dict) -> Dict[str, str]:
        """Get general schema information"""
        return {
            "bids_version": schema.get("bids_version", "unknown"),
            "schema_version": schema.get("schema_version", "unknown"),
            "num_entities": len(schema.get("objects", {}).get("entities", {})),
            "num_datatypes": len(schema.get("objects", {}).get("datatypes", {})),
            "num_metadata_fields": len(schema.get("objects", {}).get("metadata", {})),
            "num_suffixes": len(schema.get("objects", {}).get("suffixes", {})),
            "num_extensions": len(schema.get("objects", {}).get("extensions", {}))
        }

    def get_entity_order(self, schema: dict) -> List[str]:
        """
        Extract canonical entity ordering from BIDS schema.

        The BIDS specification defines a canonical order for entities in filenames.
        While the schema JSON doesn't explicitly encode this order, we extract it
        from the entity definitions and apply the BIDS-specified canonical ordering.

        Reference: BIDS Specification Appendix - Entity Table

        Returns:
            List of entity keys in canonical BIDS order
        """
        entities = schema.get('objects', {}).get('entities', {})

        # Canonical entity order as defined in BIDS specification appendix
        # This order is part of the BIDS standard and should remain stable across versions
        canonical_order = [
            'subject',      # sub
            'session',      # ses
            'task',         # task
            'acquisition',  # acq
            'ceagent',      # ce
            'reconstruction',  # rec
            'direction',    # dir
            'run',          # run
            'modality',     # mod
            'echo',         # echo
            'flip',         # flip
            'inversion',    # inv
            'mtransfer',    # mt
            'part',         # part
            'recording',    # recording
            'chunk',        # chunk
            'space',        # space
            'processing',   # proc
            'split',        # split
            'tracer',       # trc
            'sample',       # sample
            'stain',        # stain
            'tracksys',     # tracksys
            'resolution',   # res
            'density',      # den
            'label',        # label
            'description',  # desc
            'hemisphere',   # hemi
            'segmentation', # seg
            'nucleus',      # nuc
            'volume',       # voi
        ]

        # Extract entity short names in canonical order
        ordered_keys = []
        for entity_name in canonical_order:
            if entity_name in entities:
                entity_key = entities[entity_name]['name']  # Get short form (e.g., 'sub', 'ses')
                ordered_keys.append(entity_key)

        # Add any remaining entities not in canonical list (for schema extensions)
        existing_keys = set(ordered_keys)
        for entity_name, entity_def in entities.items():
            entity_key = entity_def['name']
            if entity_key not in existing_keys:
                ordered_keys.append(entity_key)

        return ordered_keys