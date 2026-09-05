/**
 * Real payloads captured from the backend generator, one per support case plus
 * one carrying couples, so the renderer is tested against what it will actually
 * be handed rather than a hand-written idealisation.
 *
 * Regenerate from backend/ with:
 *   uv run python -c "
 *   import json
 *   from app.problems.rigid_body.generator import RigidBodyGenerator
 *   g = RigidBodyGenerator()
 *   print(json.dumps({name: {'schemaVersion': 1, 'elements': [
 *       el.model_dump() for el in g.generate(seed=seed, params=params).visual_schema]}
 *     for name, seed, params in [
 *       ('pin_roller', 42, {'support_case': 2}),
 *       ('three_rollers', 7, {'support_case': 1}),
 *       ('cantilever_wall', 11, {'support_case': 3}),
 *       ('with_moments', 3, {'support_case': 2, 'num_moments': 2, 'num_loads': 2}),
 *     ]}, indent=2))"
 */

export const fixtures = {
  "pin_roller": {
    "schemaVersion": 1,
    "elements": [
      {
        "element_type": "rigid_body_path",
        "properties": {
          "path": [
            [
              1,
              1
            ],
            [
              1,
              0
            ],
            [
              0,
              0
            ],
            [
              0,
              1
            ],
            [
              0,
              2
            ]
          ]
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 0,
          "x": 1.0,
          "y": 1.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 1,
          "x": 1.0,
          "y": 0.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 2,
          "x": 0.0,
          "y": 0.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 3,
          "x": 0.0,
          "y": 1.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 4,
          "x": 0.0,
          "y": 2.0
        }
      },
      {
        "element_type": "pin",
        "properties": {
          "position": [
            0,
            1
          ],
          "rotation": 90,
          "label": "A"
        }
      },
      {
        "element_type": "roller",
        "properties": {
          "position": [
            1,
            1
          ],
          "rotation": 180,
          "label": "B"
        }
      },
      {
        "element_type": "point_load",
        "properties": {
          "position": [
            0,
            0
          ],
          "force_vector": [
            0.0,
            1.0
          ],
          "magnitude": 1.0,
          "label": "F"
        }
      },
      {
        "element_type": "point_load",
        "properties": {
          "position": [
            0,
            2
          ],
          "force_vector": [
            -1.0,
            0.0
          ],
          "magnitude": 1.0,
          "label": "F"
        }
      }
    ]
  },
  "three_rollers": {
    "schemaVersion": 1,
    "elements": [
      {
        "element_type": "rigid_body_path",
        "properties": {
          "path": [
            [
              3,
              3
            ],
            [
              2,
              3
            ],
            [
              1,
              3
            ],
            [
              1,
              2
            ],
            [
              0,
              2
            ],
            [
              0,
              1
            ],
            [
              0,
              0
            ],
            [
              1,
              0
            ],
            [
              2,
              0
            ],
            [
              2,
              1
            ],
            [
              2,
              2
            ]
          ]
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 0,
          "x": 3.0,
          "y": 3.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 1,
          "x": 2.0,
          "y": 3.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 2,
          "x": 1.0,
          "y": 3.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 3,
          "x": 1.0,
          "y": 2.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 4,
          "x": 0.0,
          "y": 2.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 5,
          "x": 0.0,
          "y": 1.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 6,
          "x": 0.0,
          "y": 0.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 7,
          "x": 1.0,
          "y": 0.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 8,
          "x": 2.0,
          "y": 0.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 9,
          "x": 2.0,
          "y": 1.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 10,
          "x": 2.0,
          "y": 2.0
        }
      },
      {
        "element_type": "roller",
        "properties": {
          "position": [
            1,
            0
          ],
          "rotation": 0,
          "label": "A"
        }
      },
      {
        "element_type": "roller",
        "properties": {
          "position": [
            3,
            3
          ],
          "rotation": 90,
          "label": "B"
        }
      },
      {
        "element_type": "roller",
        "properties": {
          "position": [
            2,
            1
          ],
          "rotation": 270,
          "label": "C"
        }
      },
      {
        "element_type": "point_load",
        "properties": {
          "position": [
            2,
            2
          ],
          "force_vector": [
            -3.0,
            0.0
          ],
          "magnitude": 3.0,
          "label": "3F"
        }
      },
      {
        "element_type": "point_load",
        "properties": {
          "position": [
            1,
            3
          ],
          "force_vector": [
            -3.0,
            0.0
          ],
          "magnitude": 3.0,
          "label": "3F"
        }
      }
    ]
  },
  "cantilever_wall": {
    "schemaVersion": 1,
    "elements": [
      {
        "element_type": "rigid_body_path",
        "properties": {
          "path": [
            [
              1,
              0
            ],
            [
              0,
              0
            ],
            [
              1,
              0
            ],
            [
              1,
              1
            ],
            [
              2,
              1
            ],
            [
              2,
              2
            ],
            [
              2,
              1
            ],
            [
              1,
              1
            ],
            [
              2,
              1
            ]
          ]
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 0,
          "x": 1.0,
          "y": 0.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 1,
          "x": 0.0,
          "y": 0.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 2,
          "x": 1.0,
          "y": 1.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 3,
          "x": 2.0,
          "y": 1.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 4,
          "x": 2.0,
          "y": 2.0
        }
      },
      {
        "element_type": "wall",
        "properties": {
          "position": [
            2,
            2
          ],
          "rotation": 0,
          "label": "A"
        }
      },
      {
        "element_type": "point_load",
        "properties": {
          "position": [
            1,
            0
          ],
          "force_vector": [
            0.0,
            -5.0
          ],
          "magnitude": 5.0,
          "label": "5F"
        }
      },
      {
        "element_type": "point_load",
        "properties": {
          "position": [
            2,
            1
          ],
          "force_vector": [
            4.0,
            0.0
          ],
          "magnitude": 4.0,
          "label": "4F"
        }
      }
    ]
  },
  "with_moments": {
    "schemaVersion": 1,
    "elements": [
      {
        "element_type": "rigid_body_path",
        "properties": {
          "path": [
            [
              0,
              2
            ],
            [
              1,
              2
            ],
            [
              2,
              2
            ],
            [
              3,
              2
            ],
            [
              4,
              2
            ],
            [
              4,
              1
            ],
            [
              4,
              0
            ],
            [
              3,
              0
            ],
            [
              4,
              0
            ],
            [
              5,
              0
            ]
          ]
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 0,
          "x": 0.0,
          "y": 2.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 1,
          "x": 1.0,
          "y": 2.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 2,
          "x": 2.0,
          "y": 2.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 3,
          "x": 3.0,
          "y": 2.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 4,
          "x": 4.0,
          "y": 2.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 5,
          "x": 4.0,
          "y": 1.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 6,
          "x": 4.0,
          "y": 0.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 7,
          "x": 3.0,
          "y": 0.0
        }
      },
      {
        "element_type": "node",
        "properties": {
          "id": 8,
          "x": 5.0,
          "y": 0.0
        }
      },
      {
        "element_type": "pin",
        "properties": {
          "position": [
            2,
            2
          ],
          "rotation": 0,
          "label": "A"
        }
      },
      {
        "element_type": "roller",
        "properties": {
          "position": [
            3,
            2
          ],
          "rotation": 180,
          "label": "B"
        }
      },
      {
        "element_type": "point_load",
        "properties": {
          "position": [
            4,
            1
          ],
          "force_vector": [
            0.0,
            -5.0
          ],
          "magnitude": 5.0,
          "label": "5F"
        }
      },
      {
        "element_type": "point_load",
        "properties": {
          "position": [
            0,
            2
          ],
          "force_vector": [
            -3.0,
            0.0
          ],
          "magnitude": 3.0,
          "label": "3F"
        }
      },
      {
        "element_type": "moment",
        "properties": {
          "position": [
            4,
            2
          ],
          "magnitude": 4.0,
          "direction": -1,
          "arrow_angle": 225,
          "arc_angle": 200,
          "label": "4Fa"
        }
      },
      {
        "element_type": "moment",
        "properties": {
          "position": [
            3,
            0
          ],
          "magnitude": 5.0,
          "direction": 1,
          "arrow_angle": 180,
          "arc_angle": 200,
          "label": "5Fa"
        }
      }
    ]
  }
} as const
